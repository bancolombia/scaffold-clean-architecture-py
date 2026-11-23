"""Orchestrate upgrade actions before dependency refresh."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

import tomli_w

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.project_detector import load_project_context
from scaffold_ca_python.core.version import get_scaffold_version
from scaffold_ca_python.factory.upgrades import UPGRADE_ACTIONS
from scaffold_ca_python.factory.upgrades.report import ActionRun, AppliedItem, UpgradeReport


class UpgradeError(RuntimeError):
    """A precondition or an upgrade action failed; the command exits with code 1."""


def git_tree_dirty(project_root: Path) -> bool | None:
    """True/False for a dirty/clean tree; None when git is missing or *project_root* is not a repository."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())


def _parse_version_parts(version: str) -> tuple[int, ...]:
    """Best-effort PEP 440 numeric tuple (ignores local segment after '+')."""
    core = version.split("+", 1)[0]
    parts = [int(chunk) for chunk in re.split(r"[.\-]", core) if chunk.isdigit()]
    return tuple(parts) if parts else (0,)


def declared_newer_than_installed(declared: str, installed: str) -> bool:
    return _parse_version_parts(declared) > _parse_version_parts(installed)


class UpgradeRunner:
    """Run every applicable action in registry order, persisting each before the next."""

    def __init__(self, project_root: Path, *, dry_run: bool = False, allow_dirty: bool = False) -> None:
        self.project_root = project_root
        self.dry_run = dry_run
        self.allow_dirty = allow_dirty
        self.diffs: list[str] = []
        self.touched: list[Path] = []

    def _builder(self) -> ModuleBuilder:
        ctx = load_project_context(self.project_root)
        return ModuleBuilder(project_root=self.project_root, project_ctx=ctx, dry_run=self.dry_run)

    def run(self) -> UpgradeReport:
        ctx = load_project_context(self.project_root)
        installed = get_scaffold_version()
        report = UpgradeReport(declared_version=ctx.scaffold_version, installed_version=installed)

        if ctx.scaffold_version is not None and declared_newer_than_installed(ctx.scaffold_version, installed):
            report.newer_than_installed = True
            reason = "declared scaffold_version is newer than installed scaffolder"
            report.action_runs = [
                ActionRun(a.name, applied=False, skipped=True, reason=reason) for a in UPGRADE_ACTIONS
            ]
            return report

        if not self.dry_run and not self.allow_dirty and any(a.applies(self._builder()) for a in UPGRADE_ACTIONS):
            self._require_clean_tree()

        any_applied = False
        for action in UPGRADE_ACTIONS:
            builder = self._builder()
            if not action.applies(builder):
                report.action_runs.append(ActionRun(action.name, applied=False, skipped=True, reason="does not apply"))
                continue
            try:
                result = action.up(builder)
                if self.dry_run:
                    self.diffs.extend(builder.preview_diffs())
                paths = builder.persist()
            except Exception as exc:
                raise UpgradeError(f"Upgrade action '{action.name}' failed: {exc}") from exc
            if not self.dry_run:
                self.touched.extend(paths)
            any_applied = any_applied or bool(result.applied)
            report.action_runs.append(
                ActionRun(action.name, applied=bool(result.applied), skipped=False, result=result)
            )
            report.automated.extend(result.applied)
            report.pending.extend(result.pending)

        if any_applied:
            self._bump_scaffold_version(report, installed)
        return report

    def _require_clean_tree(self) -> None:
        dirty = git_tree_dirty(self.project_root)
        if dirty is None:
            raise UpgradeError(
                "Cannot verify a clean git working tree (git not found or not a repository). "
                "Pass --allow-dirty to proceed."
            )
        if dirty:
            raise UpgradeError("Git working tree is not clean. Commit or stash changes, or pass --allow-dirty.")

    def _bump_scaffold_version(self, report: UpgradeReport, installed: str) -> None:
        """Align an existing ``scaffold_version`` with the installed scaffolder (actions that set it win)."""
        pyproject = self.project_root / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        section = data.get("tool", {}).get("scaffold-ca-python", {})
        if section.get("scaffold_version") in (None, installed):
            return
        if not self.dry_run:
            section["scaffold_version"] = installed
            pyproject.write_text(tomli_w.dumps(data), encoding="utf-8")
            self.touched.append(pyproject)
        report.automated.append(
            AppliedItem(kind="scaffold_version_updated", file="pyproject.toml", description=f"set to {installed}")
        )
