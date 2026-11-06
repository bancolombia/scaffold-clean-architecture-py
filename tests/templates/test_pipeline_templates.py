"""Template rendering tests for pipeline/ group — both providers."""

from scaffold_ca_python.models.context import ProjectContext
from tests.helpers import read_template as _tmpl
from tests.helpers import renderer


def _project() -> ProjectContext:
    return ProjectContext(name="my-app")


# github


def test_github_has_ruff_step() -> None:
    out = renderer.render_string(_tmpl("pipeline/github/ci.yml.jinja2"), _project().model_dump())
    assert "ruff" in out


def test_github_has_mypy_step() -> None:
    out = renderer.render_string(_tmpl("pipeline/github/ci.yml.jinja2"), _project().model_dump())
    assert "mypy" in out


def test_github_has_pytest_with_coverage() -> None:
    out = renderer.render_string(_tmpl("pipeline/github/ci.yml.jinja2"), _project().model_dump())
    assert "pytest" in out
    assert "cov" in out


def test_github_has_coverage_gate_80() -> None:
    out = renderer.render_string(_tmpl("pipeline/github/ci.yml.jinja2"), _project().model_dump())
    assert "--cov-fail-under=80" in out


# azure


def test_azure_has_ruff_step() -> None:
    out = renderer.render_string(_tmpl("pipeline/azure/azure_pipelines.yml.jinja2"), _project().model_dump())
    assert "ruff" in out


def test_azure_has_mypy_step() -> None:
    out = renderer.render_string(_tmpl("pipeline/azure/azure_pipelines.yml.jinja2"), _project().model_dump())
    assert "mypy" in out


def test_azure_has_pytest_with_coverage() -> None:
    out = renderer.render_string(_tmpl("pipeline/azure/azure_pipelines.yml.jinja2"), _project().model_dump())
    assert "pytest" in out
    assert "cov" in out


def test_azure_has_coverage_gate_80() -> None:
    out = renderer.render_string(_tmpl("pipeline/azure/azure_pipelines.yml.jinja2"), _project().model_dump())
    assert "--cov-fail-under=80" in out
