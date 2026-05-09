from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

from agent_plugin_diagnostics.cli import main
from agent_plugin_diagnostics.integrations.apps import check_real_app_integrations


def test_integrations_detect_real_command_and_config(tmp_path, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_command(bin_dir, "codex", "codex 1.2.3")
    monkeypatch.setenv("PATH", str(bin_dir))

    root = tmp_path / "workspace"
    config_dir = root / ".codex"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(
        """
[mcp_servers.docs]
command = "python"
args = ["server.py"]
""".lstrip(),
        encoding="utf-8",
    )

    report = check_real_app_integrations(root=root, home=tmp_path / "home", timeout=3)
    codex = next(client for client in report.clients if client.id == "codex")

    assert codex.status == "installed_configured"
    assert codex.commands[0].detected is True
    assert codex.commands[0].version_output == "codex 1.2.3"
    assert codex.discovered_configs == 1
    assert codex.discovered_servers == 1


def test_integrations_cli_outputs_json(tmp_path, capsys) -> None:
    config_dir = tmp_path / ".cursor"
    config_dir.mkdir()
    (config_dir / "mcp.json").write_text(
        json.dumps({"mcpServers": {"fake": {"command": sys.executable}}}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "integrations",
            str(tmp_path),
            "--home",
            str(tmp_path / "home"),
            "--format",
            "json",
            "--no-version",
        ]
    )
    output = json.loads(capsys.readouterr().out)
    cursor = next(client for client in output["clients"] if client["id"] == "cursor")

    assert exit_code == 0
    assert output["summary"]["clients"] == 10
    assert output["summary"]["discovered_configs"] == 1
    assert cursor["status"] == "configured"
    assert cursor["discovered_servers"] == 1


def test_integrations_cli_outputs_markdown(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "integrations",
            str(tmp_path),
            "--home",
            str(tmp_path / "home"),
            "--format",
            "markdown",
            "--no-version",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "# Agent Plugin Diagnostics Real App Integrations" in output
    assert "| Client | Status | Commands | Config files | Servers | Findings |" in output


def _write_fake_command(directory: Path, name: str, output: str) -> None:
    if os.name == "nt":
        command = directory / f"{name}.cmd"
        command.write_text(f"@echo off\r\necho {output}\r\n", encoding="utf-8")
        return
    command = directory / name
    command.write_text(f"#!/bin/sh\necho '{output}'\n", encoding="utf-8")
    command.chmod(command.stat().st_mode | stat.S_IXUSR)
