from __future__ import annotations

from agent_plugin_diagnostics.clients.base import DiscoveryContext, DiscoveryResult
from agent_plugin_diagnostics.clients.parsing import (
    invalid_config_finding,
    load_toml,
    no_servers_finding,
    parse_codex_servers,
)
from agent_plugin_diagnostics.core.models import ClientConfig, ConfigSource, Finding


class CodexAdapter:
    name = "codex"

    def discover(self, context: DiscoveryContext) -> DiscoveryResult:
        paths = (
            (context.root / ".codex" / "config.toml", "project"),
            (context.home / ".codex" / "config.toml", "user"),
        )
        configs: list[ClientConfig] = []
        findings: list[Finding] = []
        for path, scope in paths:
            if not path.exists():
                continue
            source = ConfigSource(client=self.name, path=path, scope=scope, format="toml")
            try:
                config = parse_codex_servers(source, load_toml(path))
            except Exception as error:
                findings.append(invalid_config_finding(source, error))
                continue
            if not config.servers:
                findings.append(no_servers_finding(source))
            configs.append(config)
        return DiscoveryResult(configs=tuple(configs), findings=tuple(findings))
