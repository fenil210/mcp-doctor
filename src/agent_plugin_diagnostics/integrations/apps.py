from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from agent_plugin_diagnostics.core.models import DiagnosticReport
from agent_plugin_diagnostics.core.workflows import audit

BaseName = Literal["home", "root"]


@dataclass(frozen=True)
class PathTemplate:
    base: BaseName
    scope: str
    parts: tuple[str, ...]

    def resolve(self, root: Path, home: Path) -> Path:
        base_path = root if self.base == "root" else home
        return base_path.joinpath(*self.parts)


@dataclass(frozen=True)
class CommandTemplate:
    name: str
    version_args: tuple[str, ...] = ("--version",)
    home_paths: tuple[tuple[str, ...], ...] = ()

    def explicit_paths(self, home: Path) -> tuple[Path, ...]:
        return tuple(home.joinpath(*parts) for parts in self.home_paths)


@dataclass(frozen=True)
class ClientDefinition:
    id: str
    display_name: str
    kind: str
    docs_url: str
    commands: tuple[CommandTemplate, ...]
    configs: tuple[PathTemplate, ...]
    note: str | None = None


@dataclass(frozen=True)
class CommandStatus:
    name: str
    detected: bool
    path: Path | None = None
    version_args: tuple[str, ...] = ()
    version_checked: bool = False
    version_ok: bool | None = None
    version_output: str | None = None
    version_error: str | None = None
    exit_code: int | None = None


@dataclass(frozen=True)
class ConfigStatus:
    path: Path
    scope: str
    exists: bool
    discovered: bool
    servers: int
    findings: int


@dataclass(frozen=True)
class ClientIntegrationStatus:
    id: str
    display_name: str
    kind: str
    docs_url: str
    status: str
    commands: tuple[CommandStatus, ...]
    configs: tuple[ConfigStatus, ...]
    discovered_configs: int
    discovered_servers: int
    findings: int
    note: str | None = None


@dataclass(frozen=True)
class IntegrationReport:
    root: Path
    home: Path
    clients: tuple[ClientIntegrationStatus, ...]
    audit_report: DiagnosticReport

    def summary(self) -> dict[str, int]:
        return {
            "clients": len(self.clients),
            "detected_clients": sum(client.status != "not_detected" for client in self.clients),
            "clients_with_commands": sum(
                any(command.detected for command in client.commands) for client in self.clients
            ),
            "installed_commands": sum(
                command.detected for client in self.clients for command in client.commands
            ),
            "config_files": sum(
                config.exists for client in self.clients for config in client.configs
            ),
            "discovered_configs": sum(client.discovered_configs for client in self.clients),
            "servers": sum(client.discovered_servers for client in self.clients),
            "findings": sum(client.findings for client in self.clients),
        }


CLIENT_DEFINITIONS: tuple[ClientDefinition, ...] = (
    ClientDefinition(
        id="claude-desktop",
        display_name="Claude Desktop",
        kind="desktop",
        docs_url="https://modelcontextprotocol.io/docs/develop/connect-local-servers",
        commands=(),
        configs=(
            PathTemplate(
                "home",
                "user",
                ("Library", "Application Support", "Claude", "claude_desktop_config.json"),
            ),
            PathTemplate(
                "home",
                "user",
                ("AppData", "Roaming", "Claude", "claude_desktop_config.json"),
            ),
        ),
        note="APD checks config files only; it does not launch the desktop app.",
    ),
    ClientDefinition(
        id="claude-code",
        display_name="Claude Code",
        kind="cli",
        docs_url="https://code.claude.com/docs/en/cli-reference",
        commands=(
            CommandTemplate(
                "claude",
                home_paths=((".local", "bin", "claude"), (".local", "bin", "claude.exe")),
            ),
        ),
        configs=(
            PathTemplate("root", "project", (".mcp.json",)),
            PathTemplate("home", "user", (".claude.json",)),
        ),
    ),
    ClientDefinition(
        id="cline",
        display_name="Cline",
        kind="cli",
        docs_url="https://docs.cline.bot/cline-cli/configuration",
        commands=(CommandTemplate("cline"),),
        configs=(
            PathTemplate(
                "home",
                "user",
                (".cline", "data", "settings", "cline_mcp_settings.json"),
            ),
        ),
    ),
    ClientDefinition(
        id="codex",
        display_name="Codex",
        kind="cli",
        docs_url="https://developers.openai.com/codex/config-reference",
        commands=(CommandTemplate("codex"),),
        configs=(
            PathTemplate("root", "project", (".codex", "config.toml")),
            PathTemplate("home", "user", (".codex", "config.toml")),
        ),
    ),
    ClientDefinition(
        id="cursor",
        display_name="Cursor",
        kind="cli/editor",
        docs_url="https://docs.cursor.com/en/cli/using",
        commands=(CommandTemplate("cursor-agent"), CommandTemplate("cursor")),
        configs=(
            PathTemplate("root", "project", (".cursor", "mcp.json")),
            PathTemplate("home", "user", (".cursor", "mcp.json")),
        ),
    ),
    ClientDefinition(
        id="opencode",
        display_name="OpenCode",
        kind="cli",
        docs_url="https://opencode.ai/docs/config",
        commands=(CommandTemplate("opencode"),),
        configs=(
            PathTemplate("root", "project", ("opencode.json",)),
            PathTemplate("home", "user", (".config", "opencode", "opencode.json")),
        ),
    ),
    ClientDefinition(
        id="roo-code",
        display_name="Roo Code",
        kind="editor-extension",
        docs_url="https://docs.roocode.com/features/mcp/using-mcp-in-roo",
        commands=(),
        configs=(PathTemplate("root", "project", (".roo", "mcp.json")),),
        note="Roo Code is checked through its documented project config, not a standalone CLI.",
    ),
    ClientDefinition(
        id="vscode",
        display_name="VS Code",
        kind="editor",
        docs_url="https://code.visualstudio.com/docs/copilot/reference/mcp-configuration",
        commands=(CommandTemplate("code"), CommandTemplate("code-insiders")),
        configs=(PathTemplate("root", "project", (".vscode", "mcp.json")),),
    ),
    ClientDefinition(
        id="windsurf",
        display_name="Windsurf",
        kind="editor",
        docs_url="https://docs.windsurf.com/windsurf/cascade/mcp",
        commands=(CommandTemplate("windsurf"),),
        configs=(
            PathTemplate("home", "user", (".codeium", "windsurf", "mcp_config.json")),
            PathTemplate("home", "user", (".codeium", "mcp_config.json")),
        ),
    ),
    ClientDefinition(
        id="zed",
        display_name="Zed",
        kind="editor",
        docs_url="https://zed.dev/docs/ai/mcp",
        commands=(CommandTemplate("zed"),),
        configs=(
            PathTemplate("root", "project", (".zed", "settings.json")),
            PathTemplate("home", "user", (".config", "zed", "settings.json")),
            PathTemplate("home", "user", (".zed", "settings.json")),
            PathTemplate("home", "user", ("AppData", "Roaming", "Zed", "settings.json")),
        ),
    ),
)


def check_real_app_integrations(
    root: Path,
    home: Path | None = None,
    timeout: float = 3.0,
    include_versions: bool = True,
) -> IntegrationReport:
    resolved_root = root.resolve()
    resolved_home = (home or Path.home()).resolve()
    audit_report = audit(root=resolved_root, home=resolved_home)
    clients = tuple(
        _check_client(
            definition,
            root=resolved_root,
            home=resolved_home,
            audit_report=audit_report,
            timeout=timeout,
            include_versions=include_versions,
        )
        for definition in CLIENT_DEFINITIONS
    )
    return IntegrationReport(
        root=resolved_root,
        home=resolved_home,
        clients=clients,
        audit_report=audit_report,
    )


def integration_report_to_dict(report: IntegrationReport) -> dict[str, Any]:
    return {
        "root": str(report.root),
        "home": str(report.home),
        "summary": report.summary(),
        "clients": [_client_to_dict(client) for client in report.clients],
    }


def render_integrations_terminal(report: IntegrationReport) -> str:
    summary = report.summary()
    lines = [
        "Agent Plugin Diagnostics Real App Integrations",
        "",
        f"Workspace: {report.root}",
        f"Home: {report.home}",
        f"Clients checked: {summary['clients']}",
        f"Detected clients: {summary['detected_clients']}",
        f"Installed commands: {summary['installed_commands']}",
        f"Config files: {summary['config_files']}",
        f"Servers: {summary['servers']}",
        f"Findings: {summary['findings']}",
        "",
        "Clients:",
    ]
    for client in report.clients:
        lines.append(
            f"- {client.display_name} [{client.status}] parsed_configs={client.discovered_configs} servers={client.discovered_servers} findings={client.findings}"
        )
        if client.commands:
            command_text = ", ".join(_format_command(command) for command in client.commands)
            lines.append(f"  commands: {command_text}")
        else:
            lines.append("  commands: no stable CLI command checked")
        existing_configs = [config for config in client.configs if config.exists]
        if existing_configs:
            config_text = ", ".join(str(config.path) for config in existing_configs)
            lines.append(f"  config files: {config_text}")
        else:
            lines.append("  config files: none found")
        if client.note:
            lines.append(f"  note: {client.note}")
    return "\n".join(lines) + "\n"


def render_integrations_markdown(report: IntegrationReport) -> str:
    summary = report.summary()
    lines = [
        "# Agent Plugin Diagnostics Real App Integrations",
        "",
        f"- Workspace: `{report.root}`",
        f"- Home: `{report.home}`",
        f"- Clients checked: {summary['clients']}",
        f"- Detected clients: {summary['detected_clients']}",
        f"- Installed commands: {summary['installed_commands']}",
        f"- Config files: {summary['config_files']}",
        f"- Servers: {summary['servers']}",
        f"- Findings: {summary['findings']}",
        "",
        "| Client | Status | Commands | Config files | Servers | Findings |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for client in report.clients:
        commands = "<br>".join(_format_command(command) for command in client.commands) or "none"
        configs = "<br>".join(str(config.path) for config in client.configs if config.exists)
        lines.append(
            f"| [{client.display_name}]({client.docs_url}) | {client.status} | {commands} | {configs or 'none'} | {client.discovered_servers} | {client.findings} |"
        )
    return "\n".join(lines) + "\n"


def render_integrations_json(report: IntegrationReport) -> str:
    return json.dumps(integration_report_to_dict(report), indent=2, sort_keys=True)


def _check_client(
    definition: ClientDefinition,
    root: Path,
    home: Path,
    audit_report: DiagnosticReport,
    timeout: float,
    include_versions: bool,
) -> ClientIntegrationStatus:
    commands = tuple(
        _check_command(command, home=home, timeout=timeout, include_versions=include_versions)
        for command in definition.commands
    )
    configs = tuple(
        _check_config(path_template, definition.id, root, home, audit_report)
        for path_template in definition.configs
    )
    discovered_configs = sum(config.discovered for config in configs)
    discovered_servers = sum(config.servers for config in configs)
    findings = sum(config.findings for config in configs)
    status = _status_for_client(commands, configs)
    return ClientIntegrationStatus(
        id=definition.id,
        display_name=definition.display_name,
        kind=definition.kind,
        docs_url=definition.docs_url,
        status=status,
        commands=commands,
        configs=configs,
        discovered_configs=discovered_configs,
        discovered_servers=discovered_servers,
        findings=findings,
        note=definition.note,
    )


def _check_command(
    command: CommandTemplate,
    home: Path,
    timeout: float,
    include_versions: bool,
) -> CommandStatus:
    detected_path = _resolve_command(command, home)
    if not detected_path:
        return CommandStatus(name=command.name, detected=False, version_args=command.version_args)
    if not include_versions:
        return CommandStatus(
            name=command.name,
            detected=True,
            path=detected_path,
            version_args=command.version_args,
        )
    return _run_version_check(command, detected_path, timeout)


def _resolve_command(command: CommandTemplate, home: Path) -> Path | None:
    resolved = shutil.which(command.name)
    if resolved:
        return Path(resolved)
    for path in command.explicit_paths(home):
        if path.exists():
            return path
    return None


def _run_version_check(command: CommandTemplate, path: Path, timeout: float) -> CommandStatus:
    try:
        completed = subprocess.run(
            [str(path), *command.version_args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return CommandStatus(
            name=command.name,
            detected=True,
            path=path,
            version_args=command.version_args,
            version_checked=True,
            version_ok=False,
            version_error=f"version command timed out after {timeout:g}s",
        )
    except OSError as error:
        return CommandStatus(
            name=command.name,
            detected=True,
            path=path,
            version_args=command.version_args,
            version_checked=True,
            version_ok=False,
            version_error=str(error),
        )
    output = _first_non_empty_line(completed.stdout, completed.stderr)
    return CommandStatus(
        name=command.name,
        detected=True,
        path=path,
        version_args=command.version_args,
        version_checked=True,
        version_ok=completed.returncode == 0,
        version_output=output,
        version_error=None if completed.returncode == 0 else output or "version command failed",
        exit_code=completed.returncode,
    )


def _check_config(
    path_template: PathTemplate,
    client_id: str,
    root: Path,
    home: Path,
    audit_report: DiagnosticReport,
) -> ConfigStatus:
    path = path_template.resolve(root, home)
    key = _path_key(path)
    server_counts = Counter(
        _path_key(config.source.path)
        for config in audit_report.configs
        if config.source.client == client_id
        for _server in config.servers
    )
    discovered_paths = {
        _path_key(config.source.path)
        for config in audit_report.configs
        if config.source.client == client_id
    }
    finding_counts = Counter(
        _path_key(finding.source.path)
        for finding in audit_report.findings
        if finding.source and finding.source.client == client_id
    )
    return ConfigStatus(
        path=path,
        scope=path_template.scope,
        exists=path.exists(),
        discovered=key in discovered_paths,
        servers=server_counts[key],
        findings=finding_counts[key],
    )


def _status_for_client(
    commands: tuple[CommandStatus, ...],
    configs: tuple[ConfigStatus, ...],
) -> str:
    has_command = any(command.detected for command in commands)
    has_config = any(config.exists for config in configs)
    if has_command and has_config:
        return "installed_configured"
    if has_command:
        return "installed"
    if has_config:
        return "configured"
    return "not_detected"


def _client_to_dict(client: ClientIntegrationStatus) -> dict[str, Any]:
    return {
        "id": client.id,
        "display_name": client.display_name,
        "kind": client.kind,
        "docs_url": client.docs_url,
        "status": client.status,
        "commands": [_command_to_dict(command) for command in client.commands],
        "configs": [_config_to_dict(config) for config in client.configs],
        "discovered_configs": client.discovered_configs,
        "discovered_servers": client.discovered_servers,
        "findings": client.findings,
        "note": client.note,
    }


def _command_to_dict(command: CommandStatus) -> dict[str, Any]:
    return {
        "name": command.name,
        "detected": command.detected,
        "path": str(command.path) if command.path else None,
        "version_args": list(command.version_args),
        "version_checked": command.version_checked,
        "version_ok": command.version_ok,
        "version_output": command.version_output,
        "version_error": command.version_error,
        "exit_code": command.exit_code,
    }


def _config_to_dict(config: ConfigStatus) -> dict[str, Any]:
    return {
        "path": str(config.path),
        "scope": config.scope,
        "exists": config.exists,
        "discovered": config.discovered,
        "servers": config.servers,
        "findings": config.findings,
    }


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def _first_non_empty_line(*values: str) -> str | None:
    for value in values:
        for line in value.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
    return None


def _format_command(command: CommandStatus) -> str:
    if not command.detected:
        return f"{command.name}: missing"
    text = f"{command.name}: {command.path}"
    if command.version_checked and command.version_output:
        text = f"{text} ({command.version_output})"
    elif command.version_checked and command.version_error:
        text = f"{text} (version check failed: {command.version_error})"
    return text
