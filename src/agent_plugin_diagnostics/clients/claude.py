from __future__ import annotations

from agent_plugin_diagnostics.clients.base import DiscoveryContext, DiscoveryResult
from agent_plugin_diagnostics.clients.parsing import (
    invalid_config_finding,
    load_json,
    no_servers_finding,
    parse_server_map,
)
from agent_plugin_diagnostics.core.models import ClientConfig, ConfigSource, Finding, ServerConfig


class ClaudeCodeAdapter:
    name = "claude-code"

    def discover(self, context: DiscoveryContext) -> DiscoveryResult:
        configs: list[ClientConfig] = []
        findings: list[Finding] = []
        project_path = context.root / ".mcp.json"
        if project_path.exists():
            source = ConfigSource(
                client=self.name, path=project_path, scope="project", format="json"
            )
            try:
                config = parse_server_map(source, load_json(project_path), "mcpServers")
            except Exception as error:
                findings.append(invalid_config_finding(source, error))
            else:
                if not config.servers:
                    findings.append(no_servers_finding(source))
                configs.append(config)

        user_path = context.home / ".claude.json"
        if user_path.exists():
            source = ConfigSource(client=self.name, path=user_path, scope="user", format="json")
            try:
                data = load_json(user_path)
            except Exception as error:
                findings.append(invalid_config_finding(source, error))
            else:
                top_level = parse_server_map(source, data, "mcpServers")
                project_servers: tuple[ServerConfig, ...] = ()
                projects = data.get("projects")
                if isinstance(projects, dict):
                    project_data = projects.get(str(context.root))
                    if isinstance(project_data, dict):
                        project_servers = parse_server_map(
                            source, project_data, "mcpServers"
                        ).servers
                servers = top_level.servers + project_servers
                if servers:
                    configs.append(ClientConfig(source=source, servers=servers))
        return DiscoveryResult(configs=tuple(configs), findings=tuple(findings))
