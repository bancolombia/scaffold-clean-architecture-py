"""Golden test: ≥70% of migration line budget applied automatically (spec 029)."""

from __future__ import annotations

import shutil
from pathlib import Path

from tests.factory.upgrades.sc001_metrics import FIXTURE, migration_line_budget, run_migration_copy

THRESHOLD = 0.70


def test_sc001_baseline_fixture_meets_automation_threshold(tmp_path: Path) -> None:
    dest = tmp_path / "legacy"
    automated, budget, pending = run_migration_copy(FIXTURE, dest)
    manual = pending
    total = budget + manual
    ratio = automated / total if total else 1.0
    assert ratio >= THRESHOLD, f"automation coverage: {ratio:.1%} ({automated}/{total} lines)"


def test_sc001_enriched_fixture_with_resource_provider(tmp_path: Path) -> None:
    """Project with an active Resource still clears the 70% automation threshold."""
    src = tmp_path / "legacy_enriched"
    shutil.copytree(FIXTURE, src, ignore=shutil.ignore_patterns(".ruff_cache", ".venv"))
    resource = src / "src" / "legacy_fixture" / "application" / "config" / "resource_container.py"
    text = resource.read_text(encoding="utf-8")
    resource.write_text(text + "\n    db_pool = providers.Resource(lambda: None)\n", encoding="utf-8")

    budget = migration_line_budget(src)
    work = tmp_path / "work"
    automated, _, pending = run_migration_copy(src, work)
    manual = max(pending, 1)
    total = budget + manual
    ratio = automated / total
    assert ratio >= THRESHOLD, f"automation coverage enriched: {ratio:.1%} ({automated}/{total})"
    assert pending >= 1
