"""Integration tests for legacy migration via scaffold up."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app

runner = CliRunner()


def _legacy_root(tmp_path: Path) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "legacy"
dependencies = ["dependency-injector==4.49.1", "pydantic-settings==2.15.0"]

[tool.scaffold-ca-python]
name = "legacy"
""".strip(),
        encoding="utf-8",
    )
    config = tmp_path / "src" / "legacy" / "application" / "config"
    config.mkdir(parents=True)
    (config / "legacy_container.py").write_text(
        "from dependency_injector import providers\nx = providers.Resource(lambda: None)\n",
        encoding="utf-8",
    )
    return tmp_path


def test_up_legacy_json_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(_legacy_root(tmp_path))
    with patch("scaffold_ca_python.commands.update_project.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        result = runner.invoke(app, ["up", "--report", "json", "--allow-dirty"], catch_exceptions=False)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "automated" in payload
    assert "pending" in payload
    kinds = {p["kind"] for p in payload["pending"]}
    assert "resource_provider" in kinds
