"""End-to-end tests on the committed 0.5.0 fixture."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "legacy_050_project"


@pytest.fixture()
def legacy_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dest = tmp_path / "legacy"
    shutil.copytree(FIXTURE, dest)
    monkeypatch.chdir(dest)
    return dest


def test_up_migrates_fixture(legacy_copy: Path) -> None:
    with patch("scaffold_ca_python.commands.update_project.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["up", "--allow-dirty"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    pyproject = (legacy_copy / "pyproject.toml").read_text(encoding="utf-8")
    assert "wireup" in pyproject
    assert "dependency-injector" not in pyproject
    config = legacy_copy / "src" / "legacy_fixture" / "application" / "config"
    assert (config / "wiring.py").is_file()
    assert not list(config.glob("*_container.py"))


def test_up_idempotent_on_migrated_fixture(legacy_copy: Path) -> None:
    with patch("scaffold_ca_python.commands.update_project.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        runner.invoke(app, ["up", "--allow-dirty"], catch_exceptions=False)
        result = runner.invoke(app, ["up", "--allow-dirty"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "wiring_created" not in result.output
