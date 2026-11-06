"""Tests for gpipe / generate-pipeline command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.helpers import strip_ansi

runner = CliRunner()

# Fixtures

# github provider


def test_github_creates_workflow_file(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / ".github" / "workflows" / "ci.yml").exists()


@pytest.mark.parametrize("tool", ["ruff", "mypy", "pytest"])
def test_github_workflow_contains_quality_tool(project_root: Path, tool: str) -> None:
    runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    content = (project_root / ".github" / "workflows" / "ci.yml").read_text()
    assert tool in content


# azure provider


def test_azure_creates_pipeline_file(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe", "--provider", "azure"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "azure-pipelines.yml").exists()


@pytest.mark.parametrize("tool", ["ruff", "mypy", "pytest"])
def test_azure_pipeline_contains_quality_tool(project_root: Path, tool: str) -> None:
    runner.invoke(app, ["gpipe", "--provider", "azure"], catch_exceptions=False)
    content = (project_root / "azure-pipelines.yml").read_text()
    assert tool in content


# Dry-run


def test_dry_run_github_writes_nothing(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe", "--provider", "github", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (project_root / ".github" / "workflows" / "ci.yml").exists()


def test_dry_run_github_prints_path(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe", "--provider", "github", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ci.yml" in result.output


def test_dry_run_azure_writes_nothing(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe", "--provider", "azure", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (project_root / "azure-pipelines.yml").exists()


# Validation errors


def test_missing_provider_exits_0_with_help(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe"], catch_exceptions=False)
    assert result.exit_code == 0


def test_missing_provider_error_hints_providers(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe"], catch_exceptions=False)
    assert "github" in result.output
    assert "azure" in result.output


def test_unknown_provider_exits_1(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe", "--provider", "jenkins"], catch_exceptions=False)
    assert result.exit_code == 1


def test_unknown_provider_error_message(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe", "--provider", "jenkins"], catch_exceptions=False)
    assert "jenkins" in result.output.lower()


def test_duplicate_github_exits_1(project_root: Path) -> None:
    runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    result = runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    assert result.exit_code == 1


def test_duplicate_github_error_message(project_root: Path) -> None:
    runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    result = runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    assert "already exists" in result.output


def test_duplicate_github_no_force_flag(project_root: Path) -> None:
    runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    result = runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "ci.yml' already exists at '.github/workflows/ci.yml'" in result.output
    assert "Hint: Remove the existing file first or choose a different provider." in result.output
    assert "--force" not in result.output


def test_no_project_root_error_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["gpipe", "--provider", "github"], catch_exceptions=False)
    assert "scaffold ca" in result.output.lower()


# : gpipe --help epilog


def test_gpipe_help_shows_provider_descriptions() -> None:
    result = runner.invoke(app, ["gpipe", "--help"])
    assert result.exit_code == 0
    assert "GitHub Actions" in result.output


def test_gpipe_help_notes_provider_required() -> None:
    result = runner.invoke(app, ["gpipe", "--help"])
    assert result.exit_code == 0
    assert "--provider is required" in strip_ansi(result.output)


def test_gpipe_help_contains_examples_section() -> None:
    result = runner.invoke(app, ["gpipe", "--help"])
    assert result.exit_code == 0
    assert "Examples" in result.output


# : no-args → help


# : injectable renderer/writer


def test_generate_pipeline_uses_injected_renderer_and_writer(
    project_root: Path,
) -> None:
    """_generate_pipeline_impl accepts renderer= and writer= kwargs and uses them."""
    from scaffold_ca_python.commands.generate_pipeline import (  # noqa: PLC0415
        _generate_pipeline_impl,
    )

    rendered: list[str] = []
    written: list[str] = []

    class FakeRenderer:
        def render(self, template_name: str, context: object) -> str:
            rendered.append(template_name)
            return "# fake"

    class FakeWriter:
        def execute(self, operations: object, *, dry_run: bool) -> list[object]:
            written.append("called")
            return []

    _generate_pipeline_impl(
        "github",
        dry_run=False,
        renderer=FakeRenderer(),  # type: ignore[arg-type]
        writer=FakeWriter(),  # type: ignore[arg-type]
    )

    assert rendered != [], "Injected renderer was not called"
    assert written != [], "Injected writer was not called"
