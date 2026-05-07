from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any

from agent_plugin_diagnostics.core.models import Finding, ServerConfig, Severity, Transport
from agent_plugin_diagnostics.core.utils import has_unexpanded_placeholder, merged_env


@dataclass(frozen=True)
class ProbeResult:
    server_id: str
    ok: bool
    tools: tuple[str, ...] = ()
    prompts: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    protocol_version: str | None = None
    server_name: str | None = None
    ping_ok: bool = False
    error: str | None = None


def probe_stdio_server(server: ServerConfig, timeout: float = 10.0) -> ProbeResult:
    if server.transport != Transport.STDIO or not server.command:
        return ProbeResult(server_id=server.id, ok=False, error="server is not a stdio server")
    if has_unexpanded_placeholder(server.command):
        return ProbeResult(
            server_id=server.id, ok=False, error="command contains unresolved placeholder"
        )

    argv = [server.command, *server.args]
    cwd = server.cwd if server.cwd and not has_unexpanded_placeholder(server.cwd) else None
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=merged_env(server.env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        reader = _LineReader(process)
        initialize = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agent-plugin-diagnostics", "version": "0.1.0"},
            },
        }
        _send(process, initialize)
        response = reader.read_json(timeout)
        if not response or response.get("error"):
            return ProbeResult(
                server_id=server.id, ok=False, error=f"initialize failed: {response}"
            )
        initialize_result = response.get("result") or {}
        if not isinstance(initialize_result, dict):
            return ProbeResult(
                server_id=server.id,
                ok=False,
                error=f"initialize returned an invalid result: {initialize_result}",
            )
        capabilities = initialize_result.get("capabilities") or {}
        if not isinstance(capabilities, dict):
            capabilities = {}
        server_info = initialize_result.get("serverInfo") or {}
        if not isinstance(server_info, dict):
            server_info = {}
        protocol_version = initialize_result.get("protocolVersion")
        server_name = server_info.get("name")
        _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        ping_result = _request(process, reader, 2, "ping", timeout)
        if ping_result is None or ping_result.get("error"):
            return ProbeResult(
                server_id=server.id,
                ok=False,
                protocol_version=str(protocol_version) if protocol_version else None,
                server_name=str(server_name) if server_name else None,
                error=f"ping failed: {ping_result}",
            )
        _send(process, {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}})
        tools_response = reader.read_json(timeout)
        if not tools_response or tools_response.get("error"):
            return ProbeResult(
                server_id=server.id, ok=False, error=f"tools/list failed: {tools_response}"
            )
        result = tools_response.get("result") or {}
        if not isinstance(result, dict):
            return ProbeResult(
                server_id=server.id, ok=False, error=f"tools/list returned invalid result: {result}"
            )
        raw_tools = result.get("tools") or []
        schema_error = _find_tool_schema_error(raw_tools)
        if schema_error:
            return ProbeResult(server_id=server.id, ok=False, error=schema_error)
        tools = tuple(
            str(tool.get("name"))
            for tool in raw_tools
            if isinstance(tool, dict) and tool.get("name")
        )
        prompts = _list_optional(
            process, reader, 4, "prompts/list", "prompts", capabilities, timeout
        )
        resources = _list_optional(
            process, reader, 5, "resources/list", "resources", capabilities, timeout
        )
        return ProbeResult(
            server_id=server.id,
            ok=True,
            tools=tools,
            prompts=prompts,
            resources=resources,
            protocol_version=str(protocol_version) if protocol_version else None,
            server_name=str(server_name) if server_name else None,
            ping_ok=True,
        )
    except Exception as error:
        return ProbeResult(server_id=server.id, ok=False, error=str(error))
    finally:
        if process:
            _terminate(process)


def probe_failure_to_finding(server: ServerConfig, result: ProbeResult) -> Finding | None:
    if result.ok:
        return None
    return Finding(
        id="APD080",
        title="Probe failed",
        severity=Severity.MEDIUM,
        category="probe",
        message=f"{server.display_name} failed MCP probe: {result.error}",
        suggestion="Run the server command manually and verify dependencies, env vars, and startup logs.",
        source=server.source,
        server_id=server.id,
        evidence=result.error,
    )


def _send(process: subprocess.Popen[str], payload: dict[str, Any]) -> None:
    if not process.stdin:
        raise RuntimeError("process stdin is closed")
    process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _request(
    process: subprocess.Popen[str],
    reader: _LineReader,
    request_id: int,
    method: str,
    timeout: float,
) -> dict[str, Any] | None:
    _send(process, {"jsonrpc": "2.0", "id": request_id, "method": method, "params": {}})
    return reader.read_json(timeout)


def _list_optional(
    process: subprocess.Popen[str],
    reader: _LineReader,
    request_id: int,
    method: str,
    capability: str,
    capabilities: dict[str, Any],
    timeout: float,
) -> tuple[str, ...]:
    if capability not in capabilities:
        return ()
    response = _request(process, reader, request_id, method, timeout)
    if not response or response.get("error"):
        raise RuntimeError(f"{method} failed: {response}")
    result = response.get("result") or {}
    if not isinstance(result, dict):
        raise RuntimeError(f"{method} returned invalid result: {result}")
    values = result.get(capability) or []
    return tuple(
        str(item.get("name") or item.get("uri")) for item in values if isinstance(item, dict)
    )


def _find_tool_schema_error(raw_tools: Any) -> str | None:
    if not isinstance(raw_tools, list):
        return "tools/list result does not contain a tools array"
    for tool in raw_tools:
        if not isinstance(tool, dict):
            return "tools/list returned a non-object tool entry"
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            return "tools/list returned a tool without a string name"
        schema = tool.get("inputSchema")
        if schema is not None and not isinstance(schema, dict):
            return f"tool {name} has invalid inputSchema"
    return None


class _LineReader:
    def __init__(self, process: subprocess.Popen[str]) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._thread = threading.Thread(target=self._read_stdout, args=(process,), daemon=True)
        self._thread.start()

    def read_json(self, timeout: float) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        return None

    def _read_stdout(self, process: subprocess.Popen[str]) -> None:
        if not process.stdout:
            return
        for line in process.stdout:
            self._queue.put(line)


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
