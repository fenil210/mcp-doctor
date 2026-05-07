from __future__ import annotations

from typing import Protocol

from agent_plugin_diagnostics.core.models import DiagnosticReport, Finding


class Check(Protocol):
    def run(self, report: DiagnosticReport) -> tuple[Finding, ...]: ...
