from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from agent_plugin_diagnostics.core.models import ConfigSource, ServerConfig, Transport
from agent_plugin_diagnostics.probes.protocol import CURRENT_PROTOCOL_VERSION
from agent_plugin_diagnostics.probes.remote import probe_remote_server
from agent_plugin_diagnostics.probes.stdio import probe_failure_to_finding, probe_stdio_server


def test_stdio_probe_lists_tools() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "fake_mcp_server.py"
    source = ConfigSource(client="cursor", path=fixture, scope="project", format="json")
    server = ServerConfig(
        id="fake",
        source=source,
        transport=Transport.STDIO,
        command=sys.executable,
        args=(str(fixture),),
    )

    result = probe_stdio_server(server, timeout=3)

    assert result.ok is True
    assert result.tools == ("ping",)
    assert result.ping_ok is True
    assert result.protocol_version == CURRENT_PROTOCOL_VERSION


def test_stdio_probe_sends_current_protocol_version(tmp_path) -> None:
    fixture = tmp_path / "version_check_server.py"
    fixture.write_text(
        """
from __future__ import annotations

import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    if method == "initialize":
        if request["params"]["protocolVersion"] != "2025-06-18":
            payload = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {"code": -32602, "message": "wrong protocol version"},
            }
        else:
            payload = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "version-check", "version": "1.0.0"},
                },
            }
    elif method == "ping":
        payload = {"jsonrpc": "2.0", "id": request["id"], "result": {}}
    elif method == "tools/list":
        payload = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"tools": [{"name": "ok", "inputSchema": {"type": "object"}}]},
        }
    else:
        continue
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\\n")
    sys.stdout.flush()
""".lstrip(),
        encoding="utf-8",
    )
    server = _stdio_server("version-check", fixture)

    result = probe_stdio_server(server, timeout=3)

    assert result.ok is True
    assert result.protocol_version == CURRENT_PROTOCOL_VERSION


def test_stdio_probe_rejects_bad_jsonrpc_envelope(tmp_path) -> None:
    fixture = tmp_path / "bad_envelope_server.py"
    fixture.write_text(
        """
from __future__ import annotations

import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    if request.get("method") == "initialize":
        sys.stdout.write(json.dumps({"id": request["id"], "result": {}}) + "\\n")
        sys.stdout.flush()
""".lstrip(),
        encoding="utf-8",
    )
    server = _stdio_server("bad-envelope", fixture)

    result = probe_stdio_server(server, timeout=3)
    finding = probe_failure_to_finding(server, result)

    assert result.ok is False
    assert result.failure_rule_id == "APD081"
    assert result.error == "initialize response must set jsonrpc to 2.0"
    assert finding is not None
    assert finding.id == "APD081"


def test_stdio_probe_rejects_tool_without_input_schema(tmp_path) -> None:
    fixture = tmp_path / "bad_tool_schema_server.py"
    fixture.write_text(
        """
from __future__ import annotations

import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    if method == "initialize":
        payload = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "bad-tool", "version": "1.0.0"},
            },
        }
    elif method == "ping":
        payload = {"jsonrpc": "2.0", "id": request["id"], "result": {}}
    elif method == "tools/list":
        payload = {"jsonrpc": "2.0", "id": request["id"], "result": {"tools": [{"name": "bad"}]}}
    else:
        continue
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\\n")
    sys.stdout.flush()
""".lstrip(),
        encoding="utf-8",
    )
    server = _stdio_server("bad-tool", fixture)

    result = probe_stdio_server(server, timeout=3)

    assert result.ok is False
    assert result.failure_rule_id == "APD081"
    assert result.error == "tool bad is missing required inputSchema"


@pytest.mark.parametrize(
    ("server_transport", "apd_transport", "path"),
    [
        ("streamable-http", Transport.HTTP, "/mcp"),
        ("sse", Transport.SSE, "/sse"),
    ],
)
def test_remote_probe_lists_tools(
    server_transport: str,
    apd_transport: Transport,
    path: str,
) -> None:
    port = _free_port()
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "fake_remote_mcp_server.py"
    process = subprocess.Popen(
        [sys.executable, str(fixture), str(port), server_transport],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_port(port)
        source = ConfigSource(client="cursor", path=fixture, scope="project", format="json")
        server = ServerConfig(
            id="fake-remote",
            source=source,
            transport=apd_transport,
            url=f"http://127.0.0.1:{port}{path}",
        )

        result = probe_remote_server(server, timeout=5)

        assert result.ok is True
        assert result.tools == ("ping_tool",)
        assert result.ping_ok is True
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError(f"server on port {port} did not start")


def _stdio_server(server_id: str, fixture: Path) -> ServerConfig:
    source = ConfigSource(client="cursor", path=fixture, scope="project", format="json")
    return ServerConfig(
        id=server_id,
        source=source,
        transport=Transport.STDIO,
        command=sys.executable,
        args=(str(fixture),),
    )
