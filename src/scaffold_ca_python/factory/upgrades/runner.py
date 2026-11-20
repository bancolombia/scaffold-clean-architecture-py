"""Orchestrate upgrade actions before dependency refresh."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from scaffold_ca_python.commands._shared import auto_format_project
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.project_detector import load_project_context
from scaffold_ca_python.core.version import get_scaffold_version
from scaffold_ca_python.factory.upgrades import UPGRADE_ACTIONS
from scaffold_ca_python.factory.upgrades.base import UpgradeAction
from scaffold_ca_python.factory.upgrades.report import ActionRun, UpgradeReport


def _git_dirty(project_root: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def _parse_version_parts(version: str) -> tuple[int, ...]:
    """Best-effort PEP 440 numeric tuple (ignores local segment after '+')."""
    core = version.split("+", 1)[0]
    parts: list[int] = []
    for chunk in re.split(r"[.\-]", core):
        if chunk.isdigit():
            parts.append(int(chunk))
    return tuple(parts) if parts else (0,)


def declared_newer_than_installed(declared: str, installed: str) -> bool:
    return _parse_version_parts(declared) > _parse_version_parts(installed)


class UpgradeRunner:
    def __init__(
        self,
        project_root: Path,
        *,
        dry_run: bool = False,
        allow_dirty: bool = False,
    ) -> None:
        self.project_root = project_root
        self.dry_run = dry_run
        self.allow_dirty = allow_dirty
        self.dry_run_diffs: list[str] = []

    def run(self) -> UpgradeReport:
        ctx = load_project_context(self.project_root)
        installed = get_scaffold_version()
        report = UpgradeReport(
            declared_version=ctx.scaffold_version,
            installed_version=installed,
            newer_than_installed=False,
        )

        if ctx.scaffold_version is not None and declared_newer_than_installed(ctx.scaffold_version, installed):
            report.newer_than_installed = True
            for action_cls in UPGRADE_ACTIONS:
                report.action_runs.append(
                    ActionRun(
                        name=action_cls.name,
                        applied=False,
                        skipped=True,
                        reason="declared scaffold_version is newer than installed scaffolder",
                    )
                )
            return report

        applicable = [a for a in UPGRADE_ACTIONS if a.applies(self._builder_for(a))]
        if applicable and not self.dry_run and not self.allow_dirty and _git_dirty(self.project_root):
            msg = "Git working tree is not clean. Commit or stash changes, or pass --allow-dirty."
            raise RuntimeError(msg)

        any_applied = False
        for action_cls in UPGRADE_ACTIONS:
            builder = self._builder_for(action_cls)
            if not action_cls.applies(builder):
                report.action_runs.append(
                    ActionRun(name=action_cls.name, applied=False, skipped=True, reason="does not apply")
                )
                continue

            result = action_cls.up(builder)
            self._persist_builder(builder)
            if self.dry_run:
                self.dry_run_diffs.extend(builder._file_writer.dry_run_diffs)
            any_applied = any_applied or bool(result.applied)
            report.action_runs.append(
                ActionRun(name=action_cls.name, applied=True, skipped=False, result=result),
            )
            report.automated.extend(result.applied)
            report.pending.extend(result.pending)

        if any_applied and not self.dry_run:
            from scaffold_ca_python.core.legacy_di_migration import write_scaffold_version

            if write_scaffold_version(self.project_root, installed, dry_run=False):
                report.scaffold_version_updated = True

        return report

    def _builder_for(self, _action: type[UpgradeAction]) -> ModuleBuilder:
        ctx = load_project_context(self.project_root)
        return ModuleBuilder(project_root=self.project_root, project_ctx=ctx, dry_run=self.dry_run)

    def _persist_builder(self, builder: ModuleBuilder) -> None:
        builder.persist()
        if not builder.dry_run:
            auto_format_project(builder.project_root)
