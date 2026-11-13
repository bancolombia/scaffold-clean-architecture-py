"""Template rendering tests for Docker-related templates."""

from scaffold_ca_python.models.context import ProjectContext
from tests.helpers import read_template as _tmpl
from tests.helpers import renderer


def _ctx() -> ProjectContext:
    return ProjectContext(name="order-service")


def test_dockerfile_has_base_image() -> None:
    out = renderer.render_string(_tmpl("project/dockerfile.jinja2"), _ctx().model_dump())
    assert "FROM python:3.13-slim" in out


def test_dockerfile_runs_project_script_from_venv() -> None:
    ctx = _ctx()
    out = renderer.render_string(_tmpl("project/dockerfile.jinja2"), ctx.model_dump())
    assert 'ENV PATH="/app/.venv/bin:$PATH"' in out
    assert f'CMD ["{ctx.python_package_script}"]' in out


def test_dockerfile_installs_uv() -> None:
    out = renderer.render_string(_tmpl("project/dockerfile.jinja2"), _ctx().model_dump())
    assert "uv" in out


def test_dockerignore_has_venv() -> None:
    out = renderer.render_string(_tmpl("project/dockerignore.jinja2"), _ctx().model_dump())
    assert ".venv" in out


def test_dockerignore_has_pycache() -> None:
    out = renderer.render_string(_tmpl("project/dockerignore.jinja2"), _ctx().model_dump())
    assert "__pycache__" in out


def test_dockerignore_has_git() -> None:
    out = renderer.render_string(_tmpl("project/dockerignore.jinja2"), _ctx().model_dump())
    assert ".git" in out
