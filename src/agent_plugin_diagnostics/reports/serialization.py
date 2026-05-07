from __future__ import annotations

from typing import Any

from agent_plugin_diagnostics.core.models import (
    ClientConfig,
    DiagnosticReport,
    Finding,
    ServerConfig,
)
from agent_plugin_diagnostics.core.utils import redact_value


def report_to_dict(report: DiagnosticReport) -> dict[str, Any]:
    return {
        "summary": {
            "configs": len(report.configs),
            "servers": len(report.servers),
            "findings": len(report.findings),
            "severity_counts": report.severity_counts(),
        },
        "configs": [_config_to_dict(config) for config in report.configs],
        "findings": [_finding_to_dict(finding) for finding in report.findings],
    }


def _config_to_dict(config: ClientConfig) -> dict[str, Any]:
    return {
        "client": config.source.client,
        "scope": config.source.scope,
        "path": str(config.source.path),
        "format": config.source.format,
        "servers": [_server_to_dict(server) for server in config.servers],
    }


def _server_to_dict(server: ServerConfig) -> dict[str, Any]:
    return {
        "id": server.id,
        "client": server.source.client,
        "scope": server.source.scope,
        "path": str(server.source.path),
        "transport": server.transport.value,
        "command": server.command,
        "args": list(server.args),
        "env": {key: redact_value(key, value) for key, value in server.env.items()},
        "url": server.url,
        "headers": {key: redact_value(key, value) for key, value in server.headers.items()},
        "cwd": server.cwd,
        "enabled": server.enabled,
    }


def _finding_to_dict(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "title": finding.title,
        "severity": finding.severity.value,
        "category": finding.category,
        "message": finding.message,
        "suggestion": finding.suggestion,
        "client": finding.source.client if finding.source else None,
        "path": str(finding.source.path) if finding.source else None,
        "scope": finding.source.scope if finding.source else None,
        "server_id": finding.server_id,
        "evidence": finding.evidence,
        "metadata": finding.metadata,
    }
