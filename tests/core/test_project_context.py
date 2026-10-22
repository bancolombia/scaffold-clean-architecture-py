"""Tests for load_project_context (T026, T027 / US3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from scaffold_ca_python.core.project_detector import load_project_context

runner = CliRunner()


# ---------------------------------------------------------------------------
# T026: load_project_context unit tests
# ---------------------------------------------------------------------------


def _write_pyproject(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_uses_tool_section_name(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path / "pyproject.toml",
        '[tool.scaffold-ca-python]\nname = "my-app"\n',
    )
    ctx = load_project_context(tmp_path)
    assert ctx.name == "my-app"
    assert ctx.python_package == "my_app"


def test_load_falls_back_to_dir_name(tmp_path: Path) -> None:
    demo_dir = tmp_path / "demo_dir"
    demo_dir.mkdir()
    _write_pyproject(demo_dir / "pyproject.toml", "[project]\nname = 'ignored'\n")
    ctx = load_project_context(demo_dir)
    assert ctx.name == "demo_dir"


def test_load_prefers_tool_section_over_project_section(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path / "pyproject.toml",
        '[project]\nname = "other-name"\n\n[tool.scaffold-ca-python]\nname = "my-app"\n',
    )
    ctx = load_project_context(tmp_path)
    assert ctx.name == "my-app"


# ---------------------------------------------------------------------------
# T027: integration regression — gep reads [tool.scaffold-ca-python].name
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    root = tmp_path / "my-app"
    monkeypatch.chdir(root)
    return root


def _rename_project_section_name(pyproject: Path) -> None:
    """Change [project].name from "my_app" to "renamed" without touching [tool.scaffold-ca-python]."""
    content = pyproject.read_text(encoding="utf-8")
    # [project].name uses snake_case "my_app"; scaffold section uses "my-app" (hyphen)
    content = content.replace('name = "my_app"', 'name = "renamed"', 1)
    pyproject.write_text(content, encoding="utf-8")


def test_gep_dry_run_uses_scaffold_name(project_root: Path) -> None:
    """gep --dry-run must use [tool.scaffold-ca-python].name even after [project].name is renamed."""
    _rename_project_section_name(project_root / "pyproject.toml")

    result = runner.invoke(app, ["gep", "--type", "generic", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "src/my_app/" in result.output


def test_gm_dry_run_uses_scaffold_name(project_root: Path) -> None:
    """gm --dry-run must use [tool.scaffold-ca-python].name even after [project].name is renamed."""
    _rename_project_section_name(project_root / "pyproject.toml")

    result = runner.invoke(app, ["gm", "--name", "order", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "src/my_app/" in result.output


def test_gep_mcp_add_tool_uses_scaffold_name(project_root: Path) -> None:
    """gep mcp + add-tool must resolve paths using [tool.scaffold-ca-python].name."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "mcp", "--add-tool", "--name", "ping"], catch_exceptions=False)
    assert result.exit_code == 0
    mcp_tools = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    assert mcp_tools.exists()
