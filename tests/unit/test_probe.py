from __future__ import annotations

import sys
from pathlib import Path

from agent_plugin_diagnostics.core.models import ConfigSource, ServerConfig, Transport
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
