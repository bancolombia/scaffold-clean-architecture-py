"""Line-count helpers for legacy → wireup migration automation coverage."""

from __future__ import annotations

import difflib
import shutil
from pathlib import Path

from scaffold_ca_python.core.project_detector import load_project_context
from scaffold_ca_python.factory.upgrades.runner import UpgradeRunner

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "legacy_050_project"

TRACKED_SUFFIXES = (
    "pyproject.toml",
    "application/config/wiring.py",
    "application/config/usecases/__init__.py",
)


def _pkg_root(project_root: Path) -> Path:
    ctx = load_project_context(project_root)
    return project_root / "src" / ctx.python_package


def migration_line_budget(project_root: Path) -> int:
    """Lines that must be added, removed, or edited for wireup (0.5.0 baseline)."""
    pkg_root = _pkg_root(project_root)
    budget = 0
    for path in pkg_root.rglob("*_container.py"):
        budget += len(path.read_text(encoding="utf-8").splitlines())
    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "dependency-injector" in line or "[tool.scaffold-ca-python]" in line:
                budget += 1
            if "asyncio_mode" in line and "auto" not in line:
                budget += 1
        if "wireup" not in text:
            budget += 3
        if "scaffold_version" not in text:
            budget += 1
    config = pkg_root / "application" / "config"
    if not (config / "wiring.py").is_file():
        budget += 17
    if not (config / "usecases" / "__init__.py").is_file():
        budget += 2
    return budget


def _line_change_count(before: str, after: str) -> int:
    a = before.splitlines()
    b = after.splitlines()
    changed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        changed += max(i2 - i1, j2 - j1)
    return changed


def automated_line_delta(before_root: Path, after_root: Path) -> int:
    """Count lines touched by migration under tracked paths and containers removed."""
    delta = 0
    ctx = load_project_context(before_root)
    pkg = ctx.python_package
    before_pkg = before_root / "src" / pkg
    after_pkg = after_root / "src" / pkg
    for path in before_pkg.rglob("*_container.py"):
        rel = path.relative_to(before_pkg)
        after_path = after_pkg / rel
        before_text = path.read_text(encoding="utf-8")
        after_text = after_path.read_text(encoding="utf-8") if after_path.is_file() else ""
        delta += _line_change_count(before_text, after_text)
    py_before = (before_root / "pyproject.toml").read_text(encoding="utf-8")
    py_after = (after_root / "pyproject.toml").read_text(encoding="utf-8")
    delta += _line_change_count(py_before, py_after)
    for suffix in ("application/config/wiring.py", "application/config/usecases/__init__.py"):
        b = before_pkg / suffix
        a = after_pkg / suffix
        if a.is_file():
            delta += _line_change_count(
                b.read_text(encoding="utf-8") if b.is_file() else "",
                a.read_text(encoding="utf-8"),
            )
    return delta


def run_migration_copy(src: Path, dest: Path) -> tuple[int, int, int]:
    """Copy fixture, run UpgradeRunner; return (automated_lines, budget, pending_items)."""
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".ruff_cache", ".venv"))
    before_snap = dest.parent / "before_snap"
    if before_snap.exists():
        shutil.rmtree(before_snap)
    shutil.copytree(dest, before_snap, ignore=shutil.ignore_patterns(".ruff_cache", ".venv"))
    budget = migration_line_budget(dest)
    report = UpgradeRunner(dest, dry_run=False, allow_dirty=True).run()
    automated = automated_line_delta(before_snap, dest)
    shutil.rmtree(before_snap)
    return automated, budget, len(report.pending)


def pending_manual_lines(report_pending_count: int) -> int:
    """Each pending item counts at least one manual line toward the migration budget."""
    return report_pending_count
