from __future__ import annotations

from pathlib import Path

from agent_plugin_diagnostics.checks.static import run_checks
from agent_plugin_diagnostics.clients.registry import discover_configs
from agent_plugin_diagnostics.core.models import DiagnosticReport, Finding, Transport
from agent_plugin_diagnostics.probes.stdio import probe_failure_to_finding, probe_stdio_server


def scan(root: Path, home: Path | None = None) -> DiagnosticReport:
    discovery = discover_configs(root=root, home=home)
    return DiagnosticReport(configs=discovery.configs, findings=discovery.findings)


def audit(root: Path, home: Path | None = None) -> DiagnosticReport:
    discovery = discover_configs(root=root, home=home)
    return run_checks(discovery.configs, discovery.findings)


def probe(root: Path, home: Path | None = None, server_id: str | None = None) -> DiagnosticReport:
    base_report = audit(root=root, home=home)
    findings: list[Finding] = list(base_report.findings)
    for server in base_report.servers:
        if server_id and server.id != server_id:
            continue
        if server.transport != Transport.STDIO:
            continue
        result = probe_stdio_server(server)
        finding = probe_failure_to_finding(server, result)
        if finding:
            findings.append(finding)
    return DiagnosticReport(configs=base_report.configs, findings=tuple(findings))
