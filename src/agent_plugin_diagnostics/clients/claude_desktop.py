from __future__ import annotations

from pathlib import Path

from agent_plugin_diagnostics.clients.base import DiscoveryContext, DiscoveryResult
from agent_plugin_diagnostics.clients.parsing import (
    invalid_config_finding,
    load_json,
    no_servers_finding,
    parse_server_map,
)
from agent_plugin_diagnostics.core.models import ClientConfig, ConfigSource, Finding


class ClaudeDesktopAdapter:
    name = "claude-desktop"

    def discover(self, context: DiscoveryContext) -> DiscoveryResult:
        configs: list[ClientConfig] = []
        findings: list[Finding] = []
        for path in _candidate_paths(context.home):
            if not path.exists():
                continue
            source = ConfigSource(client=self.name, path=path, scope="user", format="json")
            try:
                config = parse_server_map(source, load_json(path), "mcpServers")
            except Exception as error:
                findings.append(invalid_config_finding(source, error))
                continue
            if not config.servers:
                findings.append(no_servers_finding(source))
            configs.append(config)
        return DiscoveryResult(configs=tuple(configs), findings=tuple(findings))


def _candidate_paths(home: Path) -> tuple[Path, ...]:
    return (
        home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
    )
