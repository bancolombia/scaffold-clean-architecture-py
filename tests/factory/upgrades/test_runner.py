"""UpgradeRunner orchestration: registry order, idempotence, guards and scaffold_version ownership."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import ClassVar

import pytest

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.factory.upgrades.base import UpgradeAction
from scaffold_ca_python.factory.upgrades.report import AppliedItem, UpgradeResult
from scaffold_ca_python.factory.upgrades.runner import (
    UpgradeError,
    UpgradeRunner,
    declared_newer_than_installed,
    git_tree_dirty,
)
from tests.factory.upgrades.upgrade_support import LEGACY, copy_project, pinned_version, snapshot

_RUNNER = "scaffold_ca_python.factory.upgrades.runner"


def _wireup_project(root: Path, version: str = "1.0.0") -> Path:
    (root / "src" / "demo").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "demo"\ndependencies = ["wireup~=2.13.0"]\n\n'
        f'[tool.scaffold-ca-python]\nname = "demo"\nscaffold_version = "{version}"\n',
        encoding="utf-8",
    )
    return root


class _MarkerAction(UpgradeAction):
    """Replace a marker string; applies only while the marker is present."""

    name = "marker"
    description = "replace MARKER"
    calls: ClassVar[list[str]] = []

    @classmethod
    def _target(cls, builder: ModuleBuilder) -> Path:
        return builder.project_root / "src" / "demo" / "marker.txt"

    @classmethod
    def applies(cls, builder: ModuleBuilder) -> bool:
        target = cls._target(builder)
        return target.is_file() and "MARKER" in target.read_text(encoding="utf-8")

    @classmethod
    def up(cls, builder: ModuleBuilder) -> UpgradeResult:
        cls.calls.append(cls.name)
        builder.add_file(cls._target(builder), "done\n", overwrite=True)
        return UpgradeResult(applied=[AppliedItem(kind="pyproject_update", file="src/demo/marker.txt")])


class _SecondAction(_MarkerAction):
    name = "second"

    @classmethod
    def applies(cls, builder: ModuleBuilder) -> bool:
        return True

    @classmethod
    def up(cls, builder: ModuleBuilder) -> UpgradeResult:
        cls.calls.append(cls.name)
        return UpgradeResult()


class _BrokenAction(_SecondAction):
    name = "broken"

    @classmethod
    def up(cls, builder: ModuleBuilder) -> UpgradeResult:
        raise ValueError("boom")


@pytest.fixture()
def demo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = _wireup_project(tmp_path / "demo")
    (root / "src" / "demo" / "marker.txt").write_text("MARKER\n", encoding="utf-8")
    _MarkerAction.calls = []
    monkeypatch.setattr(f"{_RUNNER}.get_scaffold_version", lambda: "1.0.0")
    return root


def test_declared_newer_than_installed() -> None:
    assert declared_newer_than_installed("2.0.0", "1.0.0")
    assert not declared_newer_than_installed("1.0.0", "1.0.1.dev3+gabc")


def test_actions_run_in_registry_order(demo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_RUNNER}.UPGRADE_ACTIONS", [_MarkerAction, _SecondAction])
    report = UpgradeRunner(demo, allow_dirty=True).run()
    assert _MarkerAction.calls == ["marker", "second"]
    assert [r.name for r in report.action_runs] == ["marker", "second"]


def test_marker_action_is_idempotent(demo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_RUNNER}.UPGRADE_ACTIONS", [_MarkerAction])
    UpgradeRunner(demo, allow_dirty=True).run()
    after_first = snapshot(demo)
    report = UpgradeRunner(demo, allow_dirty=True).run()
    assert snapshot(demo) == after_first
    assert report.action_runs[0].skipped


def test_routine_up_on_wireup_project_writes_nothing(tmp_path: Path) -> None:
    root = _wireup_project(tmp_path / "demo")
    before = snapshot(root)
    with pinned_version():
        report = UpgradeRunner(root).run()
    assert snapshot(root) == before
    assert all(r.skipped for r in report.action_runs)


def test_newer_declared_version_skips_actions(demo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_RUNNER}.UPGRADE_ACTIONS", [_MarkerAction])
    monkeypatch.setattr(f"{_RUNNER}.get_scaffold_version", lambda: "0.9.0")
    report = UpgradeRunner(demo, allow_dirty=True).run()
    assert report.newer_than_installed
    assert _MarkerAction.calls == []


def test_existing_scaffold_version_is_bumped_once(demo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_RUNNER}.UPGRADE_ACTIONS", [_MarkerAction])
    monkeypatch.setattr(f"{_RUNNER}.get_scaffold_version", lambda: "1.1.0")
    report = UpgradeRunner(demo, allow_dirty=True).run()
    data = tomllib.loads((demo / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["scaffold-ca-python"]["scaffold_version"] == "1.1.0"
    assert [a.kind for a in report.automated].count("scaffold_version_updated") == 1


def test_failing_action_raises_upgrade_error(demo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_RUNNER}.UPGRADE_ACTIONS", [_BrokenAction])
    with pytest.raises(UpgradeError, match="'broken' failed: boom"):
        UpgradeRunner(demo, allow_dirty=True).run()


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _committed_legacy(tmp_path: Path) -> Path:
    root = copy_project(LEGACY, tmp_path / "legacy")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init", "--no-gpg-sign")
    return root


def test_git_tree_dirty_states(tmp_path: Path) -> None:
    assert git_tree_dirty(tmp_path) is None
    root = _committed_legacy(tmp_path)
    assert git_tree_dirty(root) is False
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    assert git_tree_dirty(root) is True


def test_dirty_tree_blocks_applicable_actions(tmp_path: Path) -> None:
    root = _committed_legacy(tmp_path)
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    before = snapshot(root)
    with pinned_version(), pytest.raises(UpgradeError, match="not clean"):
        UpgradeRunner(root).run()
    assert snapshot(root) == before


def test_non_git_tree_requires_allow_dirty(tmp_path: Path) -> None:
    root = copy_project(LEGACY, tmp_path / "legacy")
    with pinned_version(), pytest.raises(UpgradeError, match="--allow-dirty"):
        UpgradeRunner(root).run()


def test_clean_committed_tree_proceeds(tmp_path: Path) -> None:
    root = _committed_legacy(tmp_path)
    with pinned_version():
        report = UpgradeRunner(root).run()
    assert report.automated


def test_dry_run_skips_the_clean_tree_check(tmp_path: Path) -> None:
    root = copy_project(LEGACY, tmp_path / "legacy")
    with pinned_version():
        report = UpgradeRunner(root, dry_run=True).run()
    assert report.automated
