from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent_plugin_diagnostics.core.models import ClientConfig, Finding


@dataclass(frozen=True)
class DiscoveryContext:
    root: Path
    home: Path


@dataclass(frozen=True)
class DiscoveryResult:
    configs: tuple[ClientConfig, ...] = ()
    findings: tuple[Finding, ...] = ()


class ClientAdapter(Protocol):
    name: str

    def discover(self, context: DiscoveryContext) -> DiscoveryResult: ...
