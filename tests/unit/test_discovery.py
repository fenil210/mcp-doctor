from __future__ import annotations

from pathlib import Path

from agent_plugin_diagnostics.clients.registry import discover_configs
from agent_plugin_diagnostics.core.models import Transport

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_discovers_cursor_project_config() -> None:
    result = discover_configs(FIXTURES / "cursor", home=FIXTURES / "empty-home")

    servers = {server.id: server for config in result.configs for server in config.servers}

    assert servers["filesystem"].source.client == "cursor"
    assert servers["filesystem"].transport == Transport.STDIO
    assert servers["docs"].transport == Transport.HTTP


def test_discovers_json_config_with_utf8_bom(tmp_path) -> None:
    config_dir = tmp_path / ".cursor"
    config_dir.mkdir()
    (config_dir / "mcp.json").write_text(
        '{"mcpServers": {"bom": {"command": "python"}}}',
        encoding="utf-8-sig",
    )

    result = discover_configs(tmp_path, home=tmp_path / "home")

    assert result.findings == ()
    assert result.configs[0].servers[0].id == "bom"


def test_discovers_codex_project_config() -> None:
    result = discover_configs(FIXTURES / "codex", home=FIXTURES / "empty-home")

    server = result.configs[0].servers[0]

    assert server.source.client == "codex"
    assert server.id == "fetch"
    assert server.command == "uvx"


def test_discovers_claude_vscode_and_windsurf_configs() -> None:
    claude = discover_configs(FIXTURES / "claude", home=FIXTURES / "empty-home")
    vscode = discover_configs(FIXTURES / "vscode", home=FIXTURES / "empty-home")
    windsurf = discover_configs(FIXTURES / "empty-workspace", home=FIXTURES / "windsurf")

    assert claude.configs[0].source.client == "claude-code"
    assert vscode.configs[0].source.client == "vscode"
    assert windsurf.configs[0].source.client == "windsurf"


def test_discovers_additional_client_configs() -> None:
    claude_desktop = discover_configs(
        FIXTURES / "empty-workspace", home=FIXTURES / "claude-desktop"
    )
    cline = discover_configs(FIXTURES / "empty-workspace", home=FIXTURES / "cline")
    roo = discover_configs(FIXTURES / "roo", home=FIXTURES / "empty-home")
    zed = discover_configs(FIXTURES / "zed", home=FIXTURES / "empty-home")
    opencode = discover_configs(FIXTURES / "opencode", home=FIXTURES / "empty-home")

    assert claude_desktop.configs[0].source.client == "claude-desktop"
    assert cline.configs[0].source.client == "cline"
    assert roo.configs[0].source.client == "roo-code"
    assert zed.configs[0].source.client == "zed"
    assert opencode.configs[0].source.client == "opencode"
    assert opencode.configs[0].servers[0].command == "npx"
    assert opencode.configs[0].servers[0].args[0] == "-y"
