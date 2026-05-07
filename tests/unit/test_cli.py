from __future__ import annotations

import json
import sys

from agent_plugin_diagnostics.cli import main


def test_cli_scan_outputs_json(tmp_path, capsys) -> None:
    config_dir = tmp_path / ".cursor"
    config_dir.mkdir()
    (config_dir / "mcp.json").write_text(
        json.dumps({"mcpServers": {"python": {"command": sys.executable}}}),
        encoding="utf-8",
    )

    exit_code = main(["scan", str(tmp_path), "--home", str(tmp_path / "home"), "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["summary"]["servers"] == 1


def test_cli_init_outputs_codex_snippet(capsys) -> None:
    exit_code = main(["init", "--client", "codex"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "[mcp_servers.mcp-doctor]" in output
    assert 'args = ["serve-mcp"]' in output
