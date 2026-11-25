"""E2E QA: gda --type psycopg + gep restapi (mirrors docs/.qa-logs/run-psycopg-scenario.sh)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app

runner = CliRunner()


def test_psycopg_restapi_qa_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    pkg = "ms_psycopg_qa"
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", pkg], catch_exceptions=False)
    project_dir = tmp_path / pkg
    monkeypatch.chdir(project_dir)
    runner.invoke(app, ["gm", "--name", "book"], catch_exceptions=False)
    runner.invoke(app, ["guc", "--name", "book", "--uses", "book_repository"], catch_exceptions=False)
    runner.invoke(app, ["gda", "--type", "psycopg", "--gateway", "book_repository"], catch_exceptions=False)
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)

    sync = subprocess.run(["uv", "sync", "--no-progress"], cwd=project_dir, capture_output=True, text=True, timeout=180)
    if sync.returncode != 0:
        pytest.skip(f"uv sync failed: {sync.stderr}")

    def run(*cmd: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["uv", "run", *cmd], cwd=project_dir, capture_output=True, text=True, timeout=180)

    for cmd in (("ruff", "check", "."), ("mypy", f"src/{pkg}")):
        res = run(*cmd)
        assert res.returncode == 0, f"{cmd} failed:\n{res.stdout}\n{res.stderr}"

    result = run("pytest")
    assert result.returncode == 0, f"pytest failed:\n{result.stdout}\n{result.stderr}"
