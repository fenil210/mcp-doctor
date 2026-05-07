from __future__ import annotations

from agent_plugin_diagnostics.clients.base import DiscoveryContext, DiscoveryResult
from agent_plugin_diagnostics.clients.parsing import (
    invalid_config_finding,
    load_json,
    no_servers_finding,
    parse_opencode_servers,
)
from agent_plugin_diagnostics.core.models import ClientConfig, ConfigSource, Finding


class OpenCodeAdapter:
    name = "opencode"

    def discover(self, context: DiscoveryContext) -> DiscoveryResult:
        configs: list[ClientConfig] = []
        findings: list[Finding] = []
        paths = (
            (context.root / "opencode.json", "project"),
            (context.home / ".config" / "opencode" / "opencode.json", "user"),
        )
        for path, scope in paths:
            if not path.exists():
                continue
            source = ConfigSource(client=self.name, path=path, scope=scope, format="json")
            try:
                config = parse_opencode_servers(source, load_json(path))
            except Exception as error:
                findings.append(invalid_config_finding(source, error))
                continue
            if not config.servers:
                findings.append(no_servers_finding(source))
            configs.append(config)
        return DiscoveryResult(configs=tuple(configs), findings=tuple(findings))
