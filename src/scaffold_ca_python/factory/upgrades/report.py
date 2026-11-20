"""Structured upgrade report types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AppliedItem:
    kind: str
    file: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class PendingItem:
    kind: str
    file: str
    line: int
    guide_section: str
    suggested_skeleton: str | None = None


@dataclass
class UpgradeResult:
    applied: list[AppliedItem] = field(default_factory=list)
    pending: list[PendingItem] = field(default_factory=list)


@dataclass
class ActionRun:
    name: str
    applied: bool
    skipped: bool
    reason: str = ""
    result: UpgradeResult | None = None


@dataclass
class UpgradeReport:
    action_runs: list[ActionRun] = field(default_factory=list)
    automated: list[AppliedItem] = field(default_factory=list)
    pending: list[PendingItem] = field(default_factory=list)
    declared_version: str | None = None
    installed_version: str = ""
    newer_than_installed: bool = False
    scaffold_version_updated: bool = False

    def to_json_dict(self) -> dict[str, object]:
        return {
            "scaffold_version": {
                "declared": self.declared_version,
                "installed": self.installed_version,
                "newer_than_installed": self.newer_than_installed,
            },
            "automated": [
                {"kind": i.kind, "file": i.file, **({"description": i.description} if i.description else {})}
                for i in self.automated
            ],
            "pending": [
                {
                    "kind": p.kind,
                    "file": p.file,
                    "line": p.line,
                    "guide_section": p.guide_section,
                    **({"suggested_skeleton": p.suggested_skeleton} if p.suggested_skeleton else {}),
                }
                for p in self.pending
            ],
            "actions_run": [
                {
                    "name": a.name,
                    "applied": a.applied,
                    "skipped": a.skipped,
                    **({"reason": a.reason} if a.reason else {}),
                }
                for a in self.action_runs
            ],
        }
