from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from agent_plugin_diagnostics.core.models import ConfigSource, ServerConfig, Transport
from agent_plugin_diagnostics.probes.remote import probe_remote_server
from agent_plugin_diagnostics.probes.stdio import probe_stdio_server


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
