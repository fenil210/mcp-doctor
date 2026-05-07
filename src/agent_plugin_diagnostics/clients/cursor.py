from __future__ import annotations

from agent_plugin_diagnostics.clients.base import DiscoveryContext, DiscoveryResult
from agent_plugin_diagnostics.clients.parsing import (
    invalid_config_finding,
    load_json,
    no_servers_finding,
    parse_server_map,
)
from agent_plugin_diagnostics.core.models import ClientConfig, ConfigSource, Finding


class CursorAdapter:
    name = "cursor"

    def discover(self, context: DiscoveryContext) -> DiscoveryResult:
        paths = (
            (context.root / ".cursor" / "mcp.json", "project"),
            (context.home / ".cursor" / "mcp.json", "user"),
        )
        configs: list[ClientConfig] = []
        findings: list[Finding] = []
        for path, scope in paths:
            if not path.exists():
                continue
            source = ConfigSource(client=self.name, path=path, scope=scope, format="json")
            try:
                config = parse_server_map(source, load_json(path), "mcpServers")
            except Exception as error:
                findings.append(invalid_config_finding(source, error))
                continue
            if not config.servers:
                findings.append(no_servers_finding(source))
            configs.append(config)
        return DiscoveryResult(configs=tuple(configs), findings=tuple(findings))
