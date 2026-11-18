"""Template rendering tests for helper/ group."""

from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import read_template as _tmpl
from tests.helpers import renderer


def _project() -> ProjectContext:
    return ProjectContext(name="my-app")


def _ctx() -> ModuleContext:
    return ModuleContext(name="date-utils", project=_project())


def test_helper_class_name_present() -> None:
    out = renderer.render_string(_tmpl("helper/helper.py.jinja2"), _ctx().model_dump())
    assert "DateUtils" in out


def test_helper_has_wireup_injectable() -> None:
    """Wireup (): helper template must use @wireup.injectable instead of bare pass body."""
    out = renderer.render_string(_tmpl("helper/helper.py.jinja2"), _ctx().model_dump())
    assert "wireup" in out
    assert "injectable" in out


def test_helper_init_contains_docstring() -> None:
    out = renderer.render_string(_tmpl("helper/__init__.py.jinja2"), _ctx().model_dump())
    assert "DateUtils" in out


def test_test_helper_imports_class() -> None:
    out = renderer.render_string(_tmpl("helper/test_helper.py.jinja2"), _ctx().model_dump())
    assert "DateUtils" in out


def test_test_helper_has_test_function() -> None:
    out = renderer.render_string(_tmpl("helper/test_helper.py.jinja2"), _ctx().model_dump())
    assert "def test_" in out
