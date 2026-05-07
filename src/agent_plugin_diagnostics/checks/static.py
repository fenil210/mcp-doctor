from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from agent_plugin_diagnostics.checks.base import Check
from agent_plugin_diagnostics.core.models import (
    ClientConfig,
    DiagnosticReport,
    Finding,
    ServerConfig,
    Severity,
)
from agent_plugin_diagnostics.core.utils import (
    command_exists,
    expand_user_path,
    has_unexpanded_placeholder,
    is_absolute_path,
    is_loopback_url,
    is_placeholder,
    is_probably_path,
    looks_like_secret,
    referenced_env_vars,
)


class StaticConfigCheck:
    def run(self, report: DiagnosticReport) -> tuple[Finding, ...]:
        findings: list[Finding] = []
        for server in report.servers:
            if not server.enabled:
                continue
            findings.extend(_check_launcher(server))
            findings.extend(_check_command(server))
            findings.extend(_check_cwd(server))
            findings.extend(_check_arg_paths(server))
            findings.extend(_check_env(server))
            findings.extend(_check_headers(server))
            findings.extend(_check_package_pinning(server))
            findings.extend(_check_url(server))
            findings.extend(_check_interpolation(server))
            findings.extend(_check_absolute_paths(server))
            findings.extend(_check_filesystem_scope(server))
        findings.extend(_check_duplicate_servers(report))
        return tuple(findings)


def default_checks() -> tuple[Check, ...]:
    return (StaticConfigCheck(),)


def run_checks(
    configs: tuple[ClientConfig, ...],
    initial_findings: tuple[Finding, ...] = (),
) -> DiagnosticReport:
    report = DiagnosticReport(configs=configs, findings=initial_findings)
    findings = list(initial_findings)
    for check in default_checks():
        findings.extend(check.run(report))
    return DiagnosticReport(configs=configs, findings=tuple(_dedupe_findings(findings)))


def _dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    deduped: list[Finding] = []
    for finding in findings:
        if finding.fingerprint in seen:
            continue
        seen.add(finding.fingerprint)
        deduped.append(finding)
    return deduped


def _finding(
    server: ServerConfig,
    rule_id: str,
    title: str,
    severity: Severity,
    category: str,
    message: str,
    suggestion: str,
    evidence: str | None = None,
    metadata: dict[str, str] | None = None,
) -> Finding:
    return Finding(
        id=rule_id,
        title=title,
        severity=severity,
        category=category,
        message=message,
        suggestion=suggestion,
        source=server.source,
        server_id=server.id,
        evidence=evidence,
        metadata=metadata or {},
    )


def _check_launcher(server: ServerConfig) -> list[Finding]:
    if server.launcher:
        return []
    return [
        _finding(
            server,
            "APD010",
            "Server has no launcher",
            Severity.HIGH,
            "configuration",
            f"{server.display_name} has neither command nor URL.",
            "Add a stdio command or remote MCP URL.",
        )
    ]


def _check_command(server: ServerConfig) -> list[Finding]:
    if not server.command:
        return []
    if command_exists(server.command):
        return []
    return [
        _finding(
            server,
            "APD011",
            "Command is not available",
            Severity.HIGH,
            "runtime",
            f"{server.display_name} command is not available: {server.command}",
            "Install the command or update the config to point at an executable path.",
            server.command,
        )
    ]


def _check_cwd(server: ServerConfig) -> list[Finding]:
    if not server.cwd or has_unexpanded_placeholder(server.cwd):
        return []
    path = expand_user_path(server.cwd)
    if path.exists():
        return []
    return [
        _finding(
            server,
            "APD012",
            "Working directory is missing",
            Severity.MEDIUM,
            "runtime",
            f"{server.display_name} cwd does not exist: {server.cwd}",
            "Create the directory or update cwd.",
            server.cwd,
        )
    ]


def _check_arg_paths(server: ServerConfig) -> list[Finding]:
    findings: list[Finding] = []
    base = (
        Path(server.cwd)
        if server.cwd and not has_unexpanded_placeholder(server.cwd)
        else server.source.path.parent
    )
    for arg in server.args:
        if not is_probably_path(arg):
            continue
        path = expand_user_path(arg)
        if not path.is_absolute():
            path = base / path
        if path.exists():
            continue
        findings.append(
            _finding(
                server,
                "APD013",
                "Referenced argument path is missing",
                Severity.MEDIUM,
                "runtime",
                f"{server.display_name} references a missing path argument: {arg}",
                "Fix the path or document how to create it.",
                arg,
            )
        )
    return findings


def _check_env(server: ServerConfig) -> list[Finding]:
    findings: list[Finding] = []
    for key, value in server.env.items():
        for name in referenced_env_vars(value):
            if name not in os.environ:
                findings.append(
                    _finding(
                        server,
                        "APD020",
                        "Required environment variable is missing",
                        Severity.MEDIUM,
                        "environment",
                        f"{server.display_name} references unset environment variable {name}.",
                        "Set the variable or use the client's secret store.",
                        f"{key}={value}",
                    )
                )
        if looks_like_secret(key, value):
            findings.append(
                _finding(
                    server,
                    "APD021",
                    "Literal secret in configuration",
                    Severity.HIGH,
                    "security",
                    f"{server.display_name} appears to store a secret directly in env.{key}.",
                    "Move the secret into an environment variable or secret store.",
                    key,
                )
            )
    return findings


def _check_headers(server: ServerConfig) -> list[Finding]:
    findings: list[Finding] = []
    for key, value in server.headers.items():
        for name in referenced_env_vars(value):
            if name not in os.environ:
                findings.append(
                    _finding(
                        server,
                        "APD020",
                        "Required environment variable is missing",
                        Severity.MEDIUM,
                        "environment",
                        f"{server.display_name} header {key} references unset environment variable {name}.",
                        "Set the variable or use the client's secret store.",
                        f"{key}={value}",
                    )
                )
        if looks_like_secret(key, value):
            findings.append(
                _finding(
                    server,
                    "APD021",
                    "Literal secret in configuration",
                    Severity.HIGH,
                    "security",
                    f"{server.display_name} appears to store a secret directly in header {key}.",
                    "Move the secret into an environment variable or secret store.",
                    key,
                )
            )
    return findings


def _check_package_pinning(server: ServerConfig) -> list[Finding]:
    if not server.command:
        return []
    command = Path(server.command).name.lower()
    if command.endswith(".exe"):
        command = command[:-4]
    if command not in {"npx", "uvx", "pipx"}:
        return []
    package = _extract_package_name(command, server.args)
    if not package or _is_package_pinned(command, package):
        return []
    return [
        _finding(
            server,
            "APD030",
            "Package invocation is not pinned",
            Severity.MEDIUM,
            "supply-chain",
            f"{server.display_name} invokes an unpinned package: {package}",
            "Pin the package version or use a reviewed local executable.",
            package,
        )
    ]


def _extract_package_name(command: str, args: tuple[str, ...]) -> str | None:
    skip_next = False
    for index, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in {"-y", "--yes", "run", "install"}:
            continue
        if arg in {"--package", "-p"} and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith("-"):
            if arg in {"--from"}:
                skip_next = True
            continue
        if command == "pipx" and arg in {"run", "inject"}:
            continue
        return arg
    return None


def _is_package_pinned(command: str, package: str) -> bool:
    if package in {"latest", "@latest"} or package.endswith("@latest"):
        return False
    if command == "uvx":
        return "==" in package or "@" in package or package.startswith("git+")
    if package.startswith("@"):
        rest = package.split("/", 1)[1] if "/" in package else ""
        return "@" in rest
    return "@" in package or "==" in package


def _check_url(server: ServerConfig) -> list[Finding]:
    if not server.url:
        return []
    parsed = urlparse(server.url)
    if parsed.scheme == "http" and not is_loopback_url(server.url):
        return [
            _finding(
                server,
                "APD031",
                "Remote server uses plain HTTP",
                Severity.MEDIUM,
                "transport",
                f"{server.display_name} uses plain HTTP: {server.url}",
                "Use HTTPS for remote MCP servers unless this is a loopback-only endpoint.",
                server.url,
            )
        ]
    return []


def _check_interpolation(server: ServerConfig) -> list[Finding]:
    values = [server.command or "", server.cwd or "", server.url or "", *server.args]
    values.extend(server.env.values())
    values.extend(server.headers.values())
    findings: list[Finding] = []
    for value in values:
        if not value:
            continue
        if server.source.client == "cursor":
            unsupported = "${CLAUDE_PLUGIN_ROOT}" in value or "${CLAUDE_PLUGIN_DATA}" in value
        elif server.source.client == "claude-code":
            unsupported = "${workspaceFolder}" in value or "${env:" in value or "${input:" in value
        elif server.source.client == "codex":
            unsupported = "${workspaceFolder}" in value or "${input:" in value
        else:
            unsupported = False
        if unsupported:
            findings.append(
                _finding(
                    server,
                    "APD040",
                    "Interpolation syntax may not work in this client",
                    Severity.LOW,
                    "portability",
                    f"{server.display_name} uses client-specific interpolation syntax: {value}",
                    "Generate a client-specific config snippet or replace the placeholder.",
                    value,
                )
            )
    return findings


def _check_absolute_paths(server: ServerConfig) -> list[Finding]:
    if server.source.scope != "project":
        return []
    findings: list[Finding] = []
    candidates = [
        ("command", server.command or ""),
        ("cwd", server.cwd or ""),
        *((f"args[{index}]", arg) for index, arg in enumerate(server.args)),
    ]
    for field, value in candidates:
        if value and is_absolute_path(value) and not is_placeholder(value):
            findings.append(
                _finding(
                    server,
                    "APD050",
                    "Project config contains an absolute local path",
                    Severity.LOW,
                    "portability",
                    f"{server.display_name} project config contains an absolute path: {value}",
                    "Use a workspace-relative path or document the local requirement.",
                    value,
                    {"field": field},
                )
            )
    return findings


FILESYSTEM_PACKAGE_RE = re.compile(r"server-filesystem|filesystem", re.I)
BROAD_ROOTS = {"/", "\\", "~", "~/", "~\\", "C:\\", "C:/", "%USERPROFILE%"}


def _check_filesystem_scope(server: ServerConfig) -> list[Finding]:
    text = " ".join([server.command or "", *server.args])
    if not FILESYSTEM_PACKAGE_RE.search(text):
        return []
    findings: list[Finding] = []
    for arg in server.args:
        normalized = arg.strip()
        if normalized in BROAD_ROOTS:
            findings.append(
                _finding(
                    server,
                    "APD060",
                    "Filesystem server root is too broad",
                    Severity.HIGH,
                    "security",
                    f"{server.display_name} exposes a broad filesystem root: {arg}",
                    "Restrict filesystem roots to the smallest project directory needed.",
                    arg,
                )
            )
    return findings


def _check_duplicate_servers(report: DiagnosticReport) -> list[Finding]:
    by_name: dict[str, list[ServerConfig]] = defaultdict(list)
    for server in report.servers:
        by_name[server.id].append(server)
    findings: list[Finding] = []
    for server_id, servers in by_name.items():
        definitions = {
            (
                server.command,
                server.args,
                server.url,
                tuple(sorted(server.env.items())),
                tuple(sorted(server.headers.items())),
                server.source.client,
            )
            for server in servers
        }
        if len(servers) < 2 or len(definitions) <= 1:
            continue
        first = servers[0]
        findings.append(
            _finding(
                first,
                "APD070",
                "Server name collision",
                Severity.LOW,
                "usability",
                f"Server id {server_id} is configured differently in multiple client configs.",
                "Use distinct server names or align the definitions across clients.",
                server_id,
            )
        )
    return findings
