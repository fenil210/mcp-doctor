from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from agent_plugin_diagnostics.core.models import DiagnosticReport, Finding
from agent_plugin_diagnostics.reports.serialization import report_to_dict

ReportFormat = Literal["terminal", "json", "markdown", "sarif"]


def render_report(report: DiagnosticReport, output_format: ReportFormat) -> str:
    if output_format == "terminal":
        return render_terminal(report)
    if output_format == "json":
        return json.dumps(report_to_dict(report), indent=2, sort_keys=True)
    if output_format == "markdown":
        return render_markdown(report)
    if output_format == "sarif":
        return json.dumps(render_sarif(report), indent=2, sort_keys=True)
    raise ValueError(f"unsupported report format: {output_format}")


def render_terminal(report: DiagnosticReport) -> str:
    lines = [
        "Agent Plugin Diagnostics",
        "",
        f"Configs: {len(report.configs)}",
        f"Servers: {len(report.servers)}",
        f"Findings: {len(report.findings)}",
    ]
    counts = report.severity_counts()
    severity_text = (
        "Severity: " + ", ".join(f"{name}={count}" for name, count in counts.items() if count)
        if any(counts.values())
        else "Severity: none"
    )
    lines.append(severity_text)
    if report.configs:
        lines.extend(["", "Servers:"])
        for server in report.servers:
            launcher = server.command or server.url or "<missing>"
            lines.append(
                f"- {server.display_name} [{server.transport.value}] {launcher} ({server.source.scope})"
            )
    if report.findings:
        lines.extend(["", "Findings:"])
        for finding in report.findings:
            lines.extend(_terminal_finding(finding))
    return "\n".join(lines) + "\n"


def _terminal_finding(finding: Finding) -> list[str]:
    location = str(finding.source.path) if finding.source else "global"
    server = f" server={finding.server_id}" if finding.server_id else ""
    evidence = f" evidence={finding.evidence}" if finding.evidence else ""
    return [
        f"- [{finding.severity.value}] {finding.id} {finding.title}",
        f"  {finding.message}",
        f"  location={location}{server}{evidence}",
        f"  fix={finding.suggestion}",
    ]


def render_markdown(report: DiagnosticReport) -> str:
    lines = [
        "# Agent Plugin Diagnostics Report",
        "",
        f"- Configs: {len(report.configs)}",
        f"- Servers: {len(report.servers)}",
        f"- Findings: {len(report.findings)}",
        "",
        "## Servers",
        "",
    ]
    if report.servers:
        lines.extend(
            [
                "| Client | Server | Transport | Scope | Launcher |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for server in report.servers:
            launcher = server.command or server.url or ""
            lines.append(
                f"| {server.source.client} | {server.id} | {server.transport.value} | {server.source.scope} | `{_escape_table(launcher)}` |"
            )
    else:
        lines.append("No MCP servers found.")
    lines.extend(["", "## Findings", ""])
    if report.findings:
        lines.extend(
            [
                "| Severity | Rule | Client | Server | Message | Suggested fix |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for finding in report.findings:
            client = finding.source.client if finding.source else ""
            server_id = finding.server_id or ""
            lines.append(
                f"| {finding.severity.value} | {finding.id} | {client} | {server_id} | {_escape_table(finding.message)} | {_escape_table(finding.suggestion)} |"
            )
    else:
        lines.append("No findings.")
    return "\n".join(lines) + "\n"


def render_sarif(report: DiagnosticReport) -> dict[str, Any]:
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for finding in report.findings:
        rules.setdefault(
            finding.id,
            {
                "id": finding.id,
                "name": finding.title,
                "shortDescription": {"text": finding.title},
                "fullDescription": {"text": finding.message},
                "help": {"text": finding.suggestion},
            },
        )
        result: dict[str, Any] = {
            "ruleId": finding.id,
            "level": _sarif_level(finding),
            "message": {"text": finding.message},
            "properties": {
                "severity": finding.severity.value,
                "category": finding.category,
                "suggestion": finding.suggestion,
                "server_id": finding.server_id,
            },
        }
        if finding.source:
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": Path(finding.source.path).as_posix()}
                    }
                }
            ]
        results.append(result)
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Agent Plugin Diagnostics",
                        "informationUri": "https://github.com/fenil210/mcp-doctor",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }


def _sarif_level(finding: Finding) -> str:
    if finding.severity.value in {"critical", "high"}:
        return "error"
    if finding.severity.value == "medium":
        return "warning"
    return "note"


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
