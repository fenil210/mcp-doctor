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
from agent_plugin_diagnostics.probes.protocol import (
    extract_success_result,
    initialize_request,
    initialized_notification,
    validate_empty_result,
    validate_initialize_result,
    validate_prompts_result,
    validate_resources_result,
    validate_tools_result,
)


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
    failure_rule_id: str = "APD080"


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
        _send(process, initialize_request(1))
        response = reader.read_response(expected_id=1, timeout=timeout)
        initialize_result, error = extract_success_result(response, 1, "initialize")
        if error:
            return _protocol_failure(server.id, error)
        error = validate_initialize_result(initialize_result)
        if error:
            return _protocol_failure(server.id, error)
        if not isinstance(initialize_result, dict):
            raise RuntimeError("initialize result unexpectedly passed validation")
        capabilities = initialize_result["capabilities"]
        if not isinstance(capabilities, dict):
            raise RuntimeError("capabilities unexpectedly passed validation")
        server_info = initialize_result["serverInfo"]
        if not isinstance(server_info, dict):
            raise RuntimeError("serverInfo unexpectedly passed validation")
        protocol_version = initialize_result["protocolVersion"]
        server_name = server_info["name"]
        _send(process, initialized_notification())

        ping_result = _request(process, reader, 2, "ping", timeout)
        ping_payload, error = extract_success_result(ping_result, 2, "ping")
        if error:
            return _protocol_failure(
                server.id,
                error,
                protocol_version=str(protocol_version),
                server_name=str(server_name),
            )
        error = validate_empty_result(ping_payload, "ping")
        if error:
            return _protocol_failure(
                server.id,
                error,
                protocol_version=str(protocol_version),
                server_name=str(server_name),
            )

        tools_response = _request(process, reader, 3, "tools/list", timeout)
        tools_payload, error = extract_success_result(tools_response, 3, "tools/list")
        if error:
            return _protocol_failure(server.id, error)
        tools, error = validate_tools_result(tools_payload)
        if error:
            return _protocol_failure(server.id, error)
        prompts, error = _list_optional(
            process, reader, 4, "prompts/list", "prompts", capabilities, timeout
        )
        if error:
            return _protocol_failure(server.id, error)
        resources, error = _list_optional(
            process, reader, 5, "resources/list", "resources", capabilities, timeout
        )
        if error:
            return _protocol_failure(server.id, error)
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
    if result.failure_rule_id == "APD081":
        return Finding(
            id="APD081",
            title="Protocol compliance failed",
            severity=Severity.MEDIUM,
            category="protocol",
            message=f"{server.display_name} returned a non-compliant MCP protocol response: {result.error}",
            suggestion="Update the MCP server to return spec-compliant JSON-RPC 2.0 messages and MCP payloads.",
            source=server.source,
            server_id=server.id,
            evidence=result.error,
        )
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


def _protocol_failure(
    server_id: str,
    error: str,
    protocol_version: str | None = None,
    server_name: str | None = None,
) -> ProbeResult:
    return ProbeResult(
        server_id=server_id,
        ok=False,
        protocol_version=protocol_version,
        server_name=server_name,
        error=error,
        failure_rule_id="APD081",
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
    return reader.read_response(expected_id=request_id, timeout=timeout)


def _list_optional(
    process: subprocess.Popen[str],
    reader: _LineReader,
    request_id: int,
    method: str,
    capability: str,
    capabilities: dict[str, Any],
    timeout: float,
) -> tuple[tuple[str, ...], str | None]:
    if capability not in capabilities:
        return (), None
    response = _request(process, reader, request_id, method, timeout)
    result, error = extract_success_result(response, request_id, method)
    if error:
        return (), error
    if capability == "prompts":
        values, error = validate_prompts_result(result)
    elif capability == "resources":
        values, error = validate_resources_result(result)
    else:
        return (), f"unsupported optional capability: {capability}"
    if error:
        return (), error
    return values, None


class _LineReader:
    def __init__(self, process: subprocess.Popen[str]) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._thread = threading.Thread(target=self._read_stdout, args=(process,), daemon=True)
        self._thread.start()

    def read_response(self, expected_id: int, timeout: float) -> dict[str, Any] | None:
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
            if isinstance(value, dict) and value.get("id") == expected_id:
                return value
            if isinstance(value, dict) and "id" in value:
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
