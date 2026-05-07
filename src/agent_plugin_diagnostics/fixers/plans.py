from __future__ import annotations

from dataclasses import dataclass

from agent_plugin_diagnostics.core.models import Finding


@dataclass(frozen=True)
class FixPlan:
    finding: Finding
    can_apply: bool
    summary: str
    steps: tuple[str, ...]


def plan_fix(finding: Finding) -> FixPlan:
    steps = (finding.suggestion,)
    return FixPlan(
        finding=finding,
        can_apply=False,
        summary=f"Manual fix plan for {finding.id}",
        steps=steps,
    )
