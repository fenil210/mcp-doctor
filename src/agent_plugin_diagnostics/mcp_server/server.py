from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_plugin_diagnostics.clients.snippets import SUPPORTED_CLIENTS, server_config_snippet
from agent_plugin_diagnostics.core.rules import RULES
from agent_plugin_diagnostics.core.workflows import audit, scan
from agent_plugin_diagnostics.reports.serialization import report_to_dict


def run() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:
        raise SystemExit(
            "The MCP server extra is not installed. Install with: pip install 'agent-plugin-diagnostics[mcp]'"
        ) from error

    mcp = FastMCP("mcp-doctor")

    @mcp.tool()
    def scan_agent_stack(root_path: str | None = None) -> dict[str, Any]:
        root = Path(root_path or ".").resolve()
        return report_to_dict(scan(root))

    @mcp.tool()
    def audit_agent_stack(root_path: str | None = None) -> dict[str, Any]:
        root = Path(root_path or ".").resolve()
        return report_to_dict(audit(root))

    @mcp.tool()
    def explain_finding(rule_id: str) -> dict[str, Any]:
        rule = RULES.get(rule_id.upper())
        if not rule:
            return {"found": False, "rule_id": rule_id}
        return {
            "found": True,
            "id": rule.id,
            "title": rule.title,
            "severity": rule.severity.value,
            "category": rule.category,
            "description": rule.description,
            "suggestion": rule.suggestion,
        }

    @mcp.tool()
    def generate_client_config(
        server_id: str, client: str, root_path: str | None = None
    ) -> dict[str, Any]:
        if client not in SUPPORTED_CLIENTS:
            return {"found": False, "error": f"Unsupported client: {client}"}
        root = Path(root_path or ".").resolve()
        report = scan(root)
        server = next(
            (candidate for candidate in report.servers if candidate.id == server_id), None
        )
        if not server:
            return {"found": False, "server_id": server_id}
        return {
            "found": True,
            "server_id": server_id,
            "client": client,
            "snippet": server_config_snippet(server, client),
        }

    @mcp.tool()
    def list_supported_clients() -> dict[str, Any]:
        return {"clients": list(SUPPORTED_CLIENTS)}

    mcp.run(transport="stdio")
