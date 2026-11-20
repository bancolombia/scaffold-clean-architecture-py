"""UpgradeRunner guards."""

from __future__ import annotations

from pathlib import Path

import pytest

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.factory.upgrades.runner import UpgradeRunner, declared_newer_than_installed
from scaffold_ca_python.models.context import ProjectContext


def test_declared_newer_than_installed() -> None:
    assert declared_newer_than_installed("2.0.0", "1.0.0")
    assert not declared_newer_than_installed("1.0.0", "2.0.0")


def test_runner_skips_actions_when_declared_newer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "legacy"
dependencies = ["dependency-injector==4.49.1"]

[tool.scaffold-ca-python]
name = "legacy"
scaffold_version = "9.9.9"
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "legacy").mkdir(parents=True)
    monkeypatch.setattr(
        "scaffold_ca_python.factory.upgrades.runner.get_scaffold_version",
        lambda: "1.0.0",
    )
    report = UpgradeRunner(tmp_path, dry_run=True).run()
    assert report.newer_than_installed
    assert all(run.skipped for run in report.action_runs)


def test_runner_dry_run_writes_nothing(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "legacy"
dependencies = ["dependency-injector==4.49.1"]

[tool.scaffold-ca-python]
name = "legacy"
""".strip(),
        encoding="utf-8",
    )
    pkg = tmp_path / "src" / "legacy" / "application" / "config"
    pkg.mkdir(parents=True)
    (pkg / "legacy_container.py").write_text("from dependency_injector import containers\n", encoding="utf-8")
    before = pyproject.read_text(encoding="utf-8")
    UpgradeRunner(tmp_path, dry_run=True, allow_dirty=True).run()
    assert pyproject.read_text(encoding="utf-8") == before


def test_action_applies_on_dependency_injector(tmp_path: Path) -> None:
    from scaffold_ca_python.factory.upgrades.actions.upgrade_2026_11_20_dependency_injector_to_wireup import (
        UpgradeDependencyInjectorToWireup,
    )

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "legacy"
dependencies = ["dependency-injector==4.49.1"]

[tool.scaffold-ca-python]
name = "legacy"
""".strip(),
        encoding="utf-8",
    )
    ctx = ProjectContext(name="legacy", project_root=tmp_path)
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=ctx, dry_run=True)
    assert UpgradeDependencyInjectorToWireup.applies(builder)
