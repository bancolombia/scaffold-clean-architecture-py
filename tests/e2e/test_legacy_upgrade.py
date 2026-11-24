"""End-to-end: `scaffold up` migrates the committed 0.5.0 fixture to a green wireup project."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.e2e.conftest import run_quality_checks, scaffold_in
from tests.factory.upgrades.upgrade_support import LEGACY, apply_resolution, copy_project

pytestmark = pytest.mark.e2e


def test_legacy_project_upgrades_to_green_wireup_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    uv_sync_project: Callable[[Path], None],
) -> None:
    project = copy_project(LEGACY, tmp_path / "legacy-fixture")
    monkeypatch.chdir(project)
    result = scaffold_in(project, "up", "--allow-dirty")
    assert result.exit_code == 0, result.output  # type: ignore[attr-defined]
    assert "pending resource_provider" in result.output  # type: ignore[attr-defined]

    apply_resolution(project)
    uv_sync_project(project)
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    # Checklist step 1: 0.5.0 never auto-formatted generated files.
    subprocess.run(["uv", "run", "ruff", "format", "."], cwd=project, check=True, capture_output=True, env=env)
    run_quality_checks(project)

    rerun = scaffold_in(project, "up", "--dry-run", "--report", "json")
    assert rerun.exit_code == 0, rerun.output  # type: ignore[attr-defined]
    report = json.loads(rerun.stdout)  # type: ignore[attr-defined]
    assert report["pending"] == []
    assert all(a["skipped"] for a in report["actions_run"])
