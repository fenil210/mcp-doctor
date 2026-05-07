from __future__ import annotations

import json
from pathlib import Path

from agent_plugin_diagnostics.core.models import (
    ClientConfig,
    ConfigSource,
    DiagnosticReport,
    ServerConfig,
)
from agent_plugin_diagnostics.reports.renderers import render_report
from agent_plugin_diagnostics.reports.serialization import report_to_dict


def test_json_report_redacts_secret_values() -> None:
    source = ConfigSource(client="cursor", path=Path("mcp.json"), scope="project", format="json")
    report = DiagnosticReport(
        configs=(
            ClientConfig(
                source=source,
                servers=(
                    ServerConfig(
                        id="secret-server",
                        source=source,
                        command="python",
                        env={"API_KEY": "sk-redactedtestvalue"},
                    ),
                ),
            ),
        ),
        findings=(),
    )

    data = report_to_dict(report)

    assert data["configs"][0]["servers"][0]["env"]["API_KEY"] == "<redacted>"


def test_renderers_emit_machine_readable_reports() -> None:
    source = ConfigSource(client="cursor", path=Path("mcp.json"), scope="project", format="json")
    report = DiagnosticReport(
        configs=(ClientConfig(source=source, servers=(ServerConfig(id="ok", source=source),)),),
        findings=(),
    )

    json_report = json.loads(render_report(report, "json"))
    sarif_report = json.loads(render_report(report, "sarif"))

    assert json_report["summary"]["servers"] == 1
    assert sarif_report["version"] == "2.1.0"
