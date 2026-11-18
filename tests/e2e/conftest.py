"""Session fixtures for end-to-end scaffold quality checks."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.helpers import invoke_in


def scaffold_in(project_dir: Path, *args: str) -> object:
    """Invoke scaffold CLI in-process with a temporary chdir."""
    return invoke_in(project_dir, *args)


def run_quality_checks(project_dir: Path) -> None:
    """Run ruff, mypy, pytest, and scaffold vs on a generated project (uses its venv via uv)."""
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    cmds = [
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "mypy", "--strict", "src/"],
        # Template addopts enable --cov/--cov-fail-under; quality gate is ruff/mypy/vs here.
        ["uv", "run", "pytest", "-q", "--no-cov"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"{' '.join(cmd)} failed:\n{result.stdout}\n{result.stderr}"
    vs = scaffold_in(project_dir, "vs")
    assert vs.exit_code == 0, f"scaffold vs failed:\n{vs.output}"  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def uv_sync_project(tmp_path_factory: pytest.TempPathFactory) -> Callable[[Path], None]:
    """Return a function that uv syncs a project directory."""

    def _sync(project_dir: Path) -> None:
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)
        result = subprocess.run(
            ["uv", "sync", "--no-progress"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[-800:]
            if os.environ.get("CI"):
                pytest.fail(f"uv sync failed in CI:\n{result.stdout}\n{result.stderr}")
            pytest.skip(f"uv sync failed (check network or TLS configuration): {detail or 'no output'}")

    return _sync
