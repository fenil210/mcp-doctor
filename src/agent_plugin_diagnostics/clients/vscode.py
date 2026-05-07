from __future__ import annotations

from agent_plugin_diagnostics.clients.base import DiscoveryContext, DiscoveryResult
from agent_plugin_diagnostics.clients.parsing import (
    invalid_config_finding,
    load_json,
    no_servers_finding,
    parse_vscode_servers,
)
from agent_plugin_diagnostics.core.models import ConfigSource


class VSCodeAdapter:
    name = "vscode"

    def discover(self, context: DiscoveryContext) -> DiscoveryResult:
        path = context.root / ".vscode" / "mcp.json"
        if not path.exists():
            return DiscoveryResult()
        source = ConfigSource(client=self.name, path=path, scope="project", format="json")
        try:
            config = parse_vscode_servers(source, load_json(path))
        except Exception as error:
            return DiscoveryResult(findings=(invalid_config_finding(source, error),))
        findings = (no_servers_finding(source),) if not config.servers else ()
        return DiscoveryResult(configs=(config,), findings=findings)
