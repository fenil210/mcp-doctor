from __future__ import annotations

import json

from agent_plugin_diagnostics.cli import main
from agent_plugin_diagnostics.core.models import ConfigSource, DiagnosticReport, Finding, Severity
from agent_plugin_diagnostics.fixers.plans import build_fix_preview


def test_fix_dry_run_does_not_write_config(tmp_path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config_dir = tmp_path / ".cursor"
    config_dir.mkdir()
    config_path = config_dir / "mcp.json"
    config_path.write_text(
        json.dumps({"mcpServers": {"fs": {"command": "python", "args": [str(data_dir)]}}}),
        encoding="utf-8",
    )
    before = config_path.read_text(encoding="utf-8")

    exit_code = main(["fix", str(tmp_path), "--home", str(tmp_path / "home")])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Dry run only" in output
    assert json.dumps(str(data_dir)) in output
    assert config_path.read_text(encoding="utf-8") == before


def test_fix_apply_writes_config_and_backup(tmp_path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config_dir = tmp_path / ".cursor"
    config_dir.mkdir()
    config_path = config_dir / "mcp.json"
    config_path.write_text(
        json.dumps({"mcpServers": {"fs": {"command": "python", "args": [str(data_dir)]}}}),
        encoding="utf-8",
    )

    exit_code = main(["fix", str(tmp_path), "--home", str(tmp_path / "home"), "--apply"])
    output = capsys.readouterr().out
    updated = json.loads(config_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Applied patches: 1" in output
    assert updated["mcpServers"]["fs"]["args"] == ["data"]
    assert (config_dir / "mcp.json.apd.bak").exists()


def test_fix_does_not_auto_write_user_config(tmp_path) -> None:
    root = tmp_path / "project"
    data_dir = root / "data"
    data_dir.mkdir(parents=True)
    config_dir = tmp_path / "external" / ".cursor"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "mcp.json"
    config_path.write_text(
        json.dumps({"mcpServers": {"fs": {"command": "python", "args": [str(data_dir)]}}}),
        encoding="utf-8",
    )
    before = config_path.read_text(encoding="utf-8")
    source = ConfigSource(client="cursor", path=config_path, scope="project", format="json")
    report = DiagnosticReport(
        configs=(),
        findings=(
            Finding(
                id="APD050",
                title="Project config contains an absolute local path",
                severity=Severity.LOW,
                category="portability",
                message="test",
                suggestion="Use a workspace-relative path.",
                source=source,
                server_id="fs",
                evidence=str(data_dir),
            ),
        ),
    )

    preview = build_fix_preview(report=report, root=root)

    assert preview.patches == ()
    assert preview.manual_plans[0].finding.id == "APD050"
    assert config_path.read_text(encoding="utf-8") == before


def test_fix_json_output_reports_manual_plans(tmp_path, capsys) -> None:
    config_dir = tmp_path / ".cursor"
    config_dir.mkdir()
    config_path = config_dir / "mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "secret": {
                        "command": "python",
                        "env": {"API_KEY": "sk-testsecretvalue000"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "fix",
            str(tmp_path),
            "--home",
            str(tmp_path / "home"),
            "--finding",
            "APD021",
            "--format",
            "json",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["patches"] == []
    assert output["manual_plans"][0]["rule_id"] == "APD021"
