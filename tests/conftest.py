"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scaffold_ca_python.cli import app
from tests.helpers import invoke_in, runner

_runner = runner


@pytest.fixture(scope="session")
def _base_project_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create base my-app project once per session."""
    base = tmp_path_factory.mktemp("base_project")
    result = invoke_in(base, "ca", "--name", "my-app")
    assert result.exit_code == 0, result.output
    return base / "my-app"


@pytest.fixture
def project_root(_base_project_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy of the session base project for each test."""
    dest = tmp_path / "my-app"
    shutil.copytree(_base_project_template, dest)
    monkeypatch.chdir(dest)
    return dest


@pytest.fixture
def mcp_project(project_root: Path) -> Path:
    """project_root with MCP entry point already generated."""
    result = _runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return project_root


@pytest.fixture
def project_with_order_model(project_root: Path) -> Path:
    """project_root with domain model ``order`` (includes order_repository gateway)."""
    result = _runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return project_root


@pytest.fixture
def project_with_helper(project_root: Path) -> Path:
    """project_root with infrastructure helper ``log_helper``."""
    result = _runner.invoke(app, ["gh", "--name", "log_helper"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return project_root


@pytest.fixture
def project_with_use_case(project_root: Path) -> Path:
    """project_root with ``book`` use case."""
    result = _runner.invoke(app, ["guc", "--name", "book"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return project_root


@pytest.fixture
def restapi_project(project_root: Path) -> Path:
    """project_root with REST API entry point."""
    result = _runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return project_root
