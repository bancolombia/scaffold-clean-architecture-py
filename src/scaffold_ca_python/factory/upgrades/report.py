"""Structured upgrade report types."""

from __future__ import annotations

from dataclasses import dataclass, field

# Single source of truth: kind -> anchor in docs/migration/dependency-injector-to-wireup.md
# and heading in skills/migrate-di/references/recipes.md (alignment is enforced by tests).
PENDING_KINDS: dict[str, str] = {
    "resource_provider": "providers-resource",
    "configuration_provider": "providers-configuration",
    "selector_provider": "providers-selector",
    "callable_provider": "providers-callable",
    "nested_container": "nested-container",
    "provider_arguments": "provider-arguments",
    "override_in_test": "override-in-test",
    "usecase_uses_helper": "usecase-uses-helper",
    "injection_unresolved": "injection-unresolved",
    "composition_root_modified": "composition-root",
}

AUTOMATED_KINDS: frozenset[str] = frozenset(
    {
        "pyproject_update",
        "wiring_created",
        "wiring_test_created",
        "container_to_factory",
        "container_removed",
        "injectable_on_adapter",
        "provide_to_injected",
        "composition_root_replaced",
        "scaffold_version_updated",
    }
)


@dataclass(frozen=True, slots=True)
class AppliedItem:
    kind: str
    file: str
    description: str = ""

    def __post_init__(self) -> None:
        if self.kind not in AUTOMATED_KINDS:
            raise ValueError(f"Unknown automated kind: {self.kind}")


@dataclass(frozen=True, slots=True)
class PendingItem:
    kind: str
    file: str
    line: int
    suggested_skeleton: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in PENDING_KINDS:
            raise ValueError(f"Unknown pending kind: {self.kind}")

    @property
    def guide_section(self) -> str:
        return PENDING_KINDS[self.kind]


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
