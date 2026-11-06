"""Checksum-based dry-run verification tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app

runner = CliRunner()


def _dir_hash(root: Path) -> str:
    """Stable SHA-256 of all file contents + relative paths under *root*."""
    h = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(root))
            h.update(rel.encode())
            h.update(path.read_bytes())
    return h.hexdigest()


@pytest.fixture()
def project_with_model(project_root: Path) -> Path:
    runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    return project_root


@pytest.mark.parametrize(
    ("fixture_name", "invoke_args"),
    [
        ("tmp_path", ["ca", "--name", "my-app", "--dry-run"]),
        ("project_root", ["gm", "--name", "product", "--dry-run"]),
        ("project_root", ["guc", "--name", "create_order", "--dry-run"]),
        ("project_root", ["gda", "--type", "rest-consumer", "--dry-run"]),
        ("project_root", ["gep", "--type", "restapi", "--dry-run"]),
        ("project_root", ["gh", "--name", "log_helper", "--dry-run"]),
        ("project_root", ["gpipe", "--provider", "github", "--dry-run"]),
        ("project_root", ["vs", "--dry-run"]),
        ("project_with_model", ["dm", "--name", "order", "--dry-run"]),
        ("project_root", ["up", "--dry-run"]),
    ],
)
def test_dry_run_does_not_change_fs(
    fixture_name: str,
    invoke_args: list[str],
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if fixture_name == "tmp_path":
        monkeypatch.chdir(tmp_path)
        root = tmp_path
    else:
        root = request.getfixturevalue(fixture_name)

    before = _dir_hash(root)
    if invoke_args[0] == "up":
        with patch("scaffold_ca_python.commands.update_project.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            runner.invoke(app, invoke_args, catch_exceptions=False)
            mock_run.assert_not_called()
    else:
        runner.invoke(app, invoke_args, catch_exceptions=False)
    after = _dir_hash(root)
    assert before == after
