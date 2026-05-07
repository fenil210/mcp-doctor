from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Transport(StrEnum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ConfigSource:
    client: str
    path: Path
    scope: str
    format: str


@dataclass(frozen=True)
class ServerConfig:
    id: str
    source: ConfigSource
    transport: Transport = Transport.UNKNOWN
    command: str | None = None
    args: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    enabled: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return f"{self.source.client}:{self.id}"

    @property
    def launcher(self) -> str | None:
        return self.command or self.url


@dataclass(frozen=True)
class ClientConfig:
    source: ConfigSource
    servers: tuple[ServerConfig, ...]


@dataclass(frozen=True)
class Finding:
    id: str
    title: str
    severity: Severity
    category: str
    message: str
    suggestion: str
    source: ConfigSource | None = None
    server_id: str | None = None
    evidence: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        location = str(self.source.path) if self.source else "global"
        server = self.server_id or "config"
        return f"{self.id}:{location}:{server}:{self.evidence or ''}"


@dataclass(frozen=True)
class DiagnosticReport:
    configs: tuple[ClientConfig, ...]
    findings: tuple[Finding, ...]

    @property
    def servers(self) -> tuple[ServerConfig, ...]:
        return tuple(server for config in self.configs for server in config.servers)

    def severity_counts(self) -> dict[str, int]:
        counts = {severity.value: 0 for severity in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts
