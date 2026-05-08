from __future__ import annotations

import difflib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from agent_plugin_diagnostics.core.models import DiagnosticReport, Finding
from agent_plugin_diagnostics.core.utils import is_absolute_path


@dataclass(frozen=True)
class FixPlan:
    finding: Finding
    can_apply: bool
    summary: str
    steps: tuple[str, ...]


@dataclass(frozen=True)
class FixEdit:
    finding: Finding
    source_path: Path
    old_value: str
    new_value: str
    summary: str


@dataclass(frozen=True)
class FilePatch:
    path: Path
    before: str
    after: str
    edits: tuple[FixEdit, ...]

    @property
    def diff(self) -> str:
        return "".join(
            difflib.unified_diff(
                self.before.splitlines(keepends=True),
                self.after.splitlines(keepends=True),
                fromfile=f"a/{self.path.as_posix()}",
                tofile=f"b/{self.path.as_posix()}",
            )
        )


@dataclass(frozen=True)
class FixPreview:
    patches: tuple[FilePatch, ...]
    manual_plans: tuple[FixPlan, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.patches)


def plan_fix(finding: Finding) -> FixPlan:
    steps = (finding.suggestion,)
    return FixPlan(
        finding=finding,
        can_apply=False,
        summary=f"Manual fix plan for {finding.id}",
        steps=steps,
    )


def build_fix_preview(
    report: DiagnosticReport,
    root: Path,
    finding_ids: set[str] | None = None,
) -> FixPreview:
    root = root.resolve()
    patches_by_path: dict[Path, FilePatch] = {}
    manual_plans: list[FixPlan] = []
    for finding in _filter_findings(report.findings, finding_ids):
        edit = _build_edit(finding, root)
        if not edit:
            manual_plans.append(plan_fix(finding))
            continue
        patch = _apply_edit_to_patch(patches_by_path.get(edit.source_path), edit)
        if not patch:
            manual_plans.append(plan_fix(finding))
            continue
        patches_by_path[edit.source_path] = patch
    return FixPreview(
        patches=tuple(patches_by_path.values()),
        manual_plans=tuple(manual_plans),
    )


def apply_preview(preview: FixPreview, create_backups: bool = True) -> tuple[Path, ...]:
    backup_paths: list[Path] = []
    for patch in preview.patches:
        if create_backups:
            backup_path = _next_backup_path(patch.path)
            backup_path.write_text(patch.before, encoding="utf-8")
            backup_paths.append(backup_path)
        patch.path.write_text(patch.after, encoding="utf-8")
    return tuple(backup_paths)


def render_fix_preview(preview: FixPreview) -> str:
    lines: list[str] = ["Agent Plugin Diagnostics Fix Preview", ""]
    if preview.patches:
        lines.append(f"Applicable file patches: {len(preview.patches)}")
        for patch in preview.patches:
            lines.append("")
            lines.append(f"File: {patch.path}")
            for edit in patch.edits:
                lines.append(f"- {edit.finding.id} {edit.summary}")
            lines.append("")
            lines.append(patch.diff.rstrip())
    else:
        lines.append("Applicable file patches: 0")
    if preview.manual_plans:
        lines.extend(["", f"Manual plans: {len(preview.manual_plans)}"])
        for plan in preview.manual_plans:
            source = str(plan.finding.source.path) if plan.finding.source else "global"
            lines.append(f"- {plan.finding.id} {plan.finding.title} at {source}")
            lines.append(f"  {plan.summary}: {' '.join(plan.steps)}")
    return "\n".join(lines).rstrip() + "\n"


def fix_preview_to_dict(preview: FixPreview) -> dict[str, object]:
    return {
        "patches": [
            {
                "path": str(patch.path),
                "diff": patch.diff,
                "edits": [
                    {
                        "rule_id": edit.finding.id,
                        "server_id": edit.finding.server_id,
                        "old_value": edit.old_value,
                        "new_value": edit.new_value,
                        "summary": edit.summary,
                    }
                    for edit in patch.edits
                ],
            }
            for patch in preview.patches
        ],
        "manual_plans": [
            {
                "rule_id": plan.finding.id,
                "title": plan.finding.title,
                "server_id": plan.finding.server_id,
                "can_apply": plan.can_apply,
                "summary": plan.summary,
                "steps": list(plan.steps),
                "path": str(plan.finding.source.path) if plan.finding.source else None,
            }
            for plan in preview.manual_plans
        ],
    }


def _filter_findings(
    findings: Iterable[Finding],
    finding_ids: set[str] | None,
) -> Iterable[Finding]:
    for finding in findings:
        if finding_ids and finding.id not in finding_ids:
            continue
        yield finding


def _build_edit(finding: Finding, root: Path) -> FixEdit | None:
    if finding.id != "APD050" or not finding.source or not finding.evidence:
        return None
    if finding.source.format not in {"json", "toml"}:
        return None
    old_value = finding.evidence
    if not is_absolute_path(old_value):
        return None
    try:
        finding.source.path.resolve(strict=False).relative_to(root)
        absolute = Path(old_value).resolve(strict=False)
        relative = absolute.relative_to(root)
    except ValueError:
        return None
    new_value = "." if str(relative) == "." else relative.as_posix()
    return FixEdit(
        finding=finding,
        source_path=finding.source.path,
        old_value=old_value,
        new_value=new_value,
        summary=f"replace workspace-local absolute path with {new_value}",
    )


def _apply_edit_to_patch(existing: FilePatch | None, edit: FixEdit) -> FilePatch | None:
    before = existing.before if existing else edit.source_path.read_text(encoding="utf-8")
    current = existing.after if existing else before
    after = _replace_string_literal(current, edit.old_value, edit.new_value)
    if after is None or after == current:
        return None
    edits = (*existing.edits, edit) if existing else (edit,)
    return FilePatch(path=edit.source_path, before=before, after=after, edits=edits)


def _replace_string_literal(text: str, old_value: str, new_value: str) -> str | None:
    for old_literal, new_literal in _literal_candidates(old_value, new_value):
        if old_literal in text:
            return text.replace(old_literal, new_literal)
    return None


def _literal_candidates(old_value: str, new_value: str) -> tuple[tuple[str, str], ...]:
    candidates = [(json.dumps(old_value), json.dumps(new_value))]
    if "'" not in old_value and "'" not in new_value:
        candidates.append((f"'{old_value}'", f"'{new_value}'"))
    return tuple(candidates)


def _next_backup_path(path: Path) -> Path:
    candidate = path.with_name(f"{path.name}.apd.bak")
    if not candidate.exists():
        return candidate
    index = 1
    while True:
        candidate = path.with_name(f"{path.name}.apd.bak.{index}")
        if not candidate.exists():
            return candidate
        index += 1
