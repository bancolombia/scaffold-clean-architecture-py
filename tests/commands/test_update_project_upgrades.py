"""`scaffold up` with upgrade actions on the committed 0.5.0 fixture."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.factory.upgrades.upgrade_support import LEGACY, copy_project, pinned_version, snapshot

runner = CliRunner()
_RUN = "scaffold_ca_python.commands.update_project.subprocess.run"
_REAL_RUN = subprocess.run


class _UvOnly:
    """Fake ``subprocess.run`` that records/fails uv calls and runs git/ruff for real."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.uv_calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(self, cmd: list[str], **kwargs: object) -> object:
        if cmd[0] != "uv":
            return _REAL_RUN(cmd, **kwargs)  # type: ignore[call-overload]
        self.uv_calls.append((cmd, kwargs))
        if self.error is not None:
            raise self.error
        return MagicMock(returncode=0)


@pytest.fixture()
def legacy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = copy_project(LEGACY, tmp_path / "legacy")
    monkeypatch.chdir(root)
    return root


def _invoke(*args: str) -> object:
    with pinned_version():
        return runner.invoke(app, ["up", *args], catch_exceptions=False)


def test_report_json_stdout_is_only_json(legacy: Path) -> None:
    fake = _UvOnly()
    with patch(_RUN, side_effect=fake):
        result = _invoke("--report", "json", "--allow-dirty")
    assert result.exit_code == 0, result.stderr  # type: ignore[attr-defined]
    payload = json.loads(result.stdout)  # type: ignore[attr-defined]
    assert payload["pending"][0]["kind"] == "resource_provider"
    assert "Synced virtual environment" in result.stderr  # type: ignore[attr-defined]
    assert [cmd[:2] for cmd, _ in fake.uv_calls] == [["uv", "lock"], ["uv", "sync"]]
    assert all(kwargs["stdout"] is not None for _, kwargs in fake.uv_calls)


def test_dry_run_json_keeps_diffs_off_stdout(legacy: Path) -> None:
    before = snapshot(legacy)
    result = _invoke("--dry-run", "--report", "json")
    assert result.exit_code == 0  # type: ignore[attr-defined]
    json.loads(result.stdout)  # type: ignore[attr-defined]
    assert "--- a/pyproject.toml\n+++ b/pyproject.toml\n" in result.stderr  # type: ignore[attr-defined]
    assert snapshot(legacy) == before


def test_dry_run_text_prints_plain_relative_diffs(legacy: Path) -> None:
    result = _invoke("--dry-run")
    assert result.exit_code == 0  # type: ignore[attr-defined]
    out = result.stdout  # type: ignore[attr-defined]
    assert "--- a/src/legacy_fixture/application/config/container.py\n+++ /dev/null\n" in out
    assert "pending resource_provider at src/legacy_fixture/application/config/resource_container.py:10" in out
    assert str(legacy) not in out.split("Would run:")[0]


def test_upgrades_run_before_uv(legacy: Path) -> None:
    seen: list[bool] = []

    def fake_run(cmd: list[str], **kwargs: object) -> object:
        if cmd[0] != "uv":
            return _REAL_RUN(cmd, **kwargs)  # type: ignore[call-overload]
        seen.append((legacy / "src/legacy_fixture/application/config/wiring.py").exists())
        return MagicMock(returncode=0)

    with patch(_RUN, side_effect=fake_run):
        result = _invoke("--allow-dirty")
    assert result.exit_code == 0  # type: ignore[attr-defined]
    assert seen == [True, True]


def test_untouched_files_are_not_reformatted(legacy: Path) -> None:
    untouched = ["src/legacy_fixture/server.py", "src/legacy_fixture/application/config/config.py"]
    before = {f: (legacy / f).read_bytes() for f in untouched}
    with patch(_RUN, side_effect=_UvOnly()):
        assert _invoke("--allow-dirty").exit_code == 0  # type: ignore[attr-defined]
    assert {f: (legacy / f).read_bytes() for f in untouched} == before


def test_non_git_tree_without_allow_dirty_exits_1(legacy: Path) -> None:
    before = snapshot(legacy)
    fake = _UvOnly()
    with patch(_RUN, side_effect=fake):
        result = _invoke()
    assert result.exit_code == 1  # type: ignore[attr-defined]
    assert "--allow-dirty" in result.output  # type: ignore[attr-defined]
    assert fake.uv_calls == []
    assert snapshot(legacy) == before


def test_uv_failure_exits_1(legacy: Path) -> None:
    with patch(_RUN, side_effect=_UvOnly(subprocess.CalledProcessError(1, ["uv", "lock"]))):
        result = _invoke("--allow-dirty")
    assert result.exit_code == 1  # type: ignore[attr-defined]


def test_action_failure_exits_1(legacy: Path) -> None:
    with (
        patch(
            "scaffold_ca_python.factory.upgrades.actions.upgrade_2026_11_20_dependency_injector_to_wireup._Migration.run",
            side_effect=ValueError("boom"),
        ),
        patch(_RUN, side_effect=(fake := _UvOnly())),
    ):
        result = _invoke("--allow-dirty")
    assert result.exit_code == 1  # type: ignore[attr-defined]
    assert "boom" in result.output  # type: ignore[attr-defined]
    assert fake.uv_calls == []


def test_skip_upgrades_leaves_legacy_tree_untouched(legacy: Path) -> None:
    before = snapshot(legacy)
    with patch(_RUN, side_effect=_UvOnly()):
        assert _invoke("--skip-upgrades").exit_code == 0  # type: ignore[attr-defined]
    assert snapshot(legacy) == before


def _without_scaffold_section(root: Path) -> None:
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    start = text.index("[tool.scaffold-ca-python]")
    pyproject.write_text(text[:start] + text[text.index("[tool.ruff]") :], encoding="utf-8")


@pytest.mark.parametrize("cwd", [".", "src/legacy_fixture"])
def test_pre_scaffold_project_gets_adoption_hint(legacy: Path, monkeypatch: pytest.MonkeyPatch, cwd: str) -> None:
    _without_scaffold_section(legacy)
    before = snapshot(legacy)
    monkeypatch.chdir(legacy / cwd)
    result = _invoke("--dry-run")
    assert result.exit_code == 1  # type: ignore[attr-defined]
    assert result.exception is None or isinstance(result.exception, SystemExit)  # type: ignore[attr-defined]
    assert '[tool.scaffold-ca-python]\nname = "legacy-fixture"' in result.output  # type: ignore[attr-defined]
    assert snapshot(legacy) == before
