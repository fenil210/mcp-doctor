from __future__ import annotations

from agent_plugin_diagnostics.clients.base import DiscoveryContext, DiscoveryResult
from agent_plugin_diagnostics.clients.parsing import (
    invalid_config_finding,
    load_json,
    no_servers_finding,
    parse_server_map,
)
from agent_plugin_diagnostics.core.models import ClientConfig, ConfigSource, Finding


class RooCodeAdapter:
    name = "roo-code"

    def discover(self, context: DiscoveryContext) -> DiscoveryResult:
        path = context.root / ".roo" / "mcp.json"
        if not path.exists():
            return DiscoveryResult()
        source = ConfigSource(client=self.name, path=path, scope="project", format="json")
        try:
            config = parse_server_map(source, load_json(path), "mcpServers")
        except Exception as error:
            return DiscoveryResult(findings=(invalid_config_finding(source, error),))
        findings: tuple[Finding, ...] = (no_servers_finding(source),) if not config.servers else ()
        configs: tuple[ClientConfig, ...] = (config,)
        return DiscoveryResult(configs=configs, findings=findings)
