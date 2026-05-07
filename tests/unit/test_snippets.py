from __future__ import annotations

from pathlib import Path

from agent_plugin_diagnostics.clients.snippets import doctor_server_snippet, server_config_snippet
from agent_plugin_diagnostics.core.models import ConfigSource, ServerConfig, Transport


def test_doctor_snippet_supports_vscode() -> None:
    snippet = doctor_server_snippet("vscode")

    assert '"servers"' in snippet
    assert '"type": "stdio"' in snippet


def test_server_config_snippet_supports_codex() -> None:
    source = ConfigSource(client="cursor", path=Path("mcp.json"), scope="project", format="json")
    server = ServerConfig(
        id="github-tools",
        source=source,
        transport=Transport.STDIO,
        command="uvx",
        args=("mcp-server-github==1.0.0",),
        env={"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
    )

    snippet = server_config_snippet(server, "codex")

    assert "[mcp_servers.github-tools]" in snippet
    assert 'command = "uvx"' in snippet
    assert 'GITHUB_TOKEN = "${GITHUB_TOKEN}"' in snippet
