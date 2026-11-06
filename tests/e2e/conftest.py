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
    env.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")
    cmds = [
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "mypy", "--strict", "src/"],
        ["uv", "run", "pytest", "-q"],
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
        env.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")
        result = subprocess.run(
            ["uv", "sync", "--no-progress"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            if os.environ.get("CI"):
                pytest.fail(f"uv sync failed in CI:\n{result.stdout}\n{result.stderr}")
            pytest.skip("uv sync not available locally")

    return _sync
