"""Shared helpers for upgrade-action tests built on the committed 0.5.0 fixture."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from scaffold_ca_python.commands._shared import auto_format_project
from scaffold_ca_python.factory.upgrades.report import UpgradeReport
from scaffold_ca_python.factory.upgrades.runner import UpgradeRunner

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
LEGACY = FIXTURES / "legacy_050_project"
GOLDEN = FIXTURES / "upgrade_di_golden"
RESOLUTION = FIXTURES / "upgrade_di_resolution"
PINNED_VERSION = "1.0.0"
_IGNORED = shutil.ignore_patterns(".venv", "__pycache__", ".ruff_cache", ".pytest_cache", ".mypy_cache", "uv.lock")
_ACTION = "scaffold_ca_python.factory.upgrades.actions.upgrade_2026_11_20_dependency_injector_to_wireup"


def copy_project(source: Path, dest: Path) -> Path:
    shutil.copytree(source, dest, ignore=_IGNORED)
    return dest


@contextmanager
def pinned_version(version: str = PINNED_VERSION) -> Iterator[None]:
    with (
        patch(f"{_ACTION}.get_scaffold_version", return_value=version),
        patch("scaffold_ca_python.factory.upgrades.runner.get_scaffold_version", return_value=version),
    ):
        yield


def snapshot(root: Path) -> dict[str, bytes]:
    skip = {".venv", "__pycache__", ".ruff_cache", ".pytest_cache", ".mypy_cache"}
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not skip.intersection(p.relative_to(root).parts) and p.name != "uv.lock"
    }


def migrate(root: Path, *, dry_run: bool = False) -> tuple[UpgradeReport, UpgradeRunner]:
    """Run upgrades like ``scaffold up --allow-dirty`` does, without the uv steps."""
    runner = UpgradeRunner(root, dry_run=dry_run, allow_dirty=True)
    with pinned_version():
        report = runner.run()
    if runner.touched:
        auto_format_project(root, runner.touched)
    return report, runner


def apply_resolution(root: Path) -> None:
    """Apply the committed manual resolution of the fixture's pending items."""
    for rel in (RESOLUTION / "DELETED").read_text(encoding="utf-8").split():
        (root / rel).unlink()
    for path in RESOLUTION.rglob("*.py"):
        target = root / path.relative_to(RESOLUTION)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def reference(tmp_path: Path) -> Path:
    """Golden output plus manual resolution: the fully migrated 1.0.0 project."""
    root = copy_project(GOLDEN, tmp_path / "reference")
    apply_resolution(root)
    return root
