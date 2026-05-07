from __future__ import annotations

from pathlib import Path

from agent_plugin_diagnostics.checks.static import run_checks
from agent_plugin_diagnostics.core.models import ClientConfig, ConfigSource, ServerConfig, Transport


def test_static_checks_find_security_and_portability_issues() -> None:
    source = ConfigSource(
        client="cursor",
        path=Path(".cursor/mcp.json"),
        scope="project",
        format="json",
    )
    config = ClientConfig(
        source=source,
        servers=(
            ServerConfig(
                id="filesystem",
                source=source,
                transport=Transport.STDIO,
                command="npx",
                args=("-y", "@modelcontextprotocol/server-filesystem", "/"),
                env={"API_TOKEN": "sk-testsecretvalue000"},
                url=None,
            ),
            ServerConfig(
                id="remote",
                source=source,
                transport=Transport.HTTP,
                url="http://example.com/mcp",
            ),
        ),
    )

    report = run_checks((config,))
    rule_ids = {finding.id for finding in report.findings}

    assert {"APD021", "APD030", "APD031", "APD060"}.issubset(rule_ids)


def test_static_checks_find_duplicate_server_names() -> None:
    source_a = ConfigSource(client="cursor", path=Path("a.json"), scope="project", format="json")
    source_b = ConfigSource(client="codex", path=Path("b.toml"), scope="project", format="toml")
    configs = (
        ClientConfig(
            source=source_a,
            servers=(ServerConfig(id="tools", source=source_a, command="python"),),
        ),
        ClientConfig(
            source=source_b,
            servers=(ServerConfig(id="tools", source=source_b, command="node"),),
        ),
    )

    report = run_checks(configs)

    assert any(finding.id == "APD070" for finding in report.findings)
