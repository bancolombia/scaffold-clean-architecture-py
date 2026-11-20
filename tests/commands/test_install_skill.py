"""Tests for install-skill command."""

from pathlib import Path

from typer.testing import CliRunner

from scaffold_ca_python.cli import app

runner = CliRunner()


def test_install_skill_creates_cursor_skill(project_root: Path) -> None:
    result = runner.invoke(
        app,
        ["install-skill", "migrate-di", "--target", "cursor"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    dest = project_root / ".cursor" / "skills" / "migrate-di" / "SKILL.md"
    assert dest.is_file()


def test_install_skill_refuses_without_force(project_root: Path) -> None:
    runner.invoke(app, ["install-skill", "migrate-di", "--target", "cursor"], catch_exceptions=False)
    result = runner.invoke(app, ["install-skill", "migrate-di", "--target", "cursor"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "already installed" in result.output.lower() or "⚠" in result.output
