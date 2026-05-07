from __future__ import annotations

from dataclasses import dataclass

from agent_plugin_diagnostics.core.models import Severity


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: Severity
    category: str
    description: str
    suggestion: str


RULES: dict[str, Rule] = {
    "APD001": Rule(
        id="APD001",
        title="Invalid configuration file",
        severity=Severity.HIGH,
        category="configuration",
        description="The config file could not be parsed as the expected format.",
        suggestion="Fix the syntax error or regenerate the client configuration.",
    ),
    "APD002": Rule(
        id="APD002",
        title="No server definitions found",
        severity=Severity.LOW,
        category="configuration",
        description="The file exists, but no MCP server definitions were found in a supported section.",
        suggestion="Add a supported server map such as mcpServers or servers.",
    ),
    "APD010": Rule(
        id="APD010",
        title="Server has no launcher",
        severity=Severity.HIGH,
        category="configuration",
        description="The server does not define a command or URL.",
        suggestion="Add a stdio command or a remote MCP URL for this server.",
    ),
    "APD011": Rule(
        id="APD011",
        title="Command is not available",
        severity=Severity.HIGH,
        category="runtime",
        description="The configured stdio command cannot be found on PATH or at the given path.",
        suggestion="Install the missing command or replace it with an absolute path that exists.",
    ),
    "APD012": Rule(
        id="APD012",
        title="Working directory is missing",
        severity=Severity.MEDIUM,
        category="runtime",
        description="The configured working directory does not exist.",
        suggestion="Create the directory or update the cwd value.",
    ),
    "APD013": Rule(
        id="APD013",
        title="Referenced argument path is missing",
        severity=Severity.MEDIUM,
        category="runtime",
        description="A command argument appears to reference a local file or directory that does not exist.",
        suggestion="Fix the path, make it relative to the correct workspace, or document the required file.",
    ),
    "APD020": Rule(
        id="APD020",
        title="Required environment variable is missing",
        severity=Severity.MEDIUM,
        category="environment",
        description="A config value references an environment variable that is not currently set.",
        suggestion="Set the variable in your shell or use the client-specific secret mechanism.",
    ),
    "APD021": Rule(
        id="APD021",
        title="Literal secret in configuration",
        severity=Severity.HIGH,
        category="security",
        description="A config file appears to contain a raw token, API key, or secret.",
        suggestion="Move the secret into an environment variable or the client secret store.",
    ),
    "APD030": Rule(
        id="APD030",
        title="Package invocation is not pinned",
        severity=Severity.MEDIUM,
        category="supply-chain",
        description="A package-manager launcher appears to use an unpinned or latest package version.",
        suggestion="Pin package versions or use a reviewed local executable.",
    ),
    "APD031": Rule(
        id="APD031",
        title="Remote server uses plain HTTP",
        severity=Severity.MEDIUM,
        category="transport",
        description="A remote MCP server URL uses HTTP instead of HTTPS.",
        suggestion="Use HTTPS for remote MCP servers unless the URL is loopback-only.",
    ),
    "APD040": Rule(
        id="APD040",
        title="Interpolation syntax may not work in this client",
        severity=Severity.LOW,
        category="portability",
        description="The config uses placeholder syntax that is not known to be supported by this client.",
        suggestion="Use the variable syntax documented by the target client or generate a client-specific config.",
    ),
    "APD050": Rule(
        id="APD050",
        title="Project config contains an absolute local path",
        severity=Severity.LOW,
        category="portability",
        description="Absolute paths in shared project config usually do not work on another contributor's machine.",
        suggestion="Use workspace-relative paths or document the local setup requirement.",
    ),
    "APD060": Rule(
        id="APD060",
        title="Filesystem server root is too broad",
        severity=Severity.HIGH,
        category="security",
        description="A filesystem MCP server appears to expose a broad system or home directory.",
        suggestion="Restrict filesystem roots to the smallest project directory needed.",
    ),
    "APD070": Rule(
        id="APD070",
        title="Server name collision",
        severity=Severity.LOW,
        category="usability",
        description="More than one discovered client config uses the same server id for different definitions.",
        suggestion="Use distinct server names or align the definitions across clients.",
    ),
    "APD080": Rule(
        id="APD080",
        title="Probe failed",
        severity=Severity.MEDIUM,
        category="probe",
        description="The server could not complete a controlled MCP startup or discovery probe.",
        suggestion="Run the command manually, inspect server logs, and verify required dependencies.",
    ),
}


def get_rule(rule_id: str) -> Rule | None:
    return RULES.get(rule_id)
