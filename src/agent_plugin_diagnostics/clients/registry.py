from __future__ import annotations

from pathlib import Path

from agent_plugin_diagnostics.clients.base import ClientAdapter, DiscoveryContext, DiscoveryResult
from agent_plugin_diagnostics.clients.claude import ClaudeCodeAdapter
from agent_plugin_diagnostics.clients.claude_desktop import ClaudeDesktopAdapter
from agent_plugin_diagnostics.clients.cline import ClineAdapter
from agent_plugin_diagnostics.clients.codex import CodexAdapter
from agent_plugin_diagnostics.clients.cursor import CursorAdapter
from agent_plugin_diagnostics.clients.opencode import OpenCodeAdapter
from agent_plugin_diagnostics.clients.roo import RooCodeAdapter
from agent_plugin_diagnostics.clients.vscode import VSCodeAdapter
from agent_plugin_diagnostics.clients.windsurf import WindsurfAdapter
from agent_plugin_diagnostics.clients.zed import ZedAdapter
from agent_plugin_diagnostics.core.models import ClientConfig, Finding


def default_adapters() -> tuple[ClientAdapter, ...]:
    return (
        ClaudeDesktopAdapter(),
        ClaudeCodeAdapter(),
        ClineAdapter(),
        CodexAdapter(),
        CursorAdapter(),
        OpenCodeAdapter(),
        RooCodeAdapter(),
        VSCodeAdapter(),
        WindsurfAdapter(),
        ZedAdapter(),
    )


def discover_configs(
    root: Path,
    home: Path | None = None,
    adapters: tuple[ClientAdapter, ...] | None = None,
) -> DiscoveryResult:
    context = DiscoveryContext(root=root.resolve(), home=(home or Path.home()).resolve())
    configs: list[ClientConfig] = []
    findings: list[Finding] = []
    for adapter in adapters or default_adapters():
        result = adapter.discover(context)
        configs.extend(result.configs)
        findings.extend(result.findings)
    return DiscoveryResult(configs=tuple(configs), findings=tuple(findings))
