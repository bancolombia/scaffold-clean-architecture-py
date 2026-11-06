"""Template rendering tests for use_case/ group."""

import ast
import importlib.resources

from scaffold_ca_python.core.template_renderer import TemplateRenderer
from scaffold_ca_python.models.context import ModuleContext, ProjectContext

renderer = TemplateRenderer()


def _project() -> ProjectContext:
    return ProjectContext(name="my-app")


def _ctx() -> ModuleContext:
    return ModuleContext(name="create-order", project=_project())


def _tmpl(name: str) -> str:
    return importlib.resources.files("scaffold_ca_python.templates").joinpath(name).read_text(encoding="utf-8")


def test_use_case_class_name_present() -> None:
    out = renderer.render_string(_tmpl("use_case/use_case.py.jinja2"), _ctx().model_dump())
    assert "CreateOrder" in out


def test_use_case_has_async_execute() -> None:
    out = renderer.render_string(_tmpl("use_case/use_case.py.jinja2"), _ctx().model_dump())
    assert "async def execute" in out


def test_use_case_class_has_use_case_suffix() -> None:
    out = renderer.render_string(_tmpl("use_case/use_case.py.jinja2"), _ctx().model_dump())
    assert "CreateOrderUseCase" in out


def test_test_use_case_imports_class() -> None:
    out = renderer.render_string(_tmpl("use_case/test_use_case.py.jinja2"), _ctx().model_dump())
    assert "CreateOrderUseCase" in out


def test_test_use_case_has_async_test() -> None:
    out = renderer.render_string(_tmpl("use_case/test_use_case.py.jinja2"), _ctx().model_dump())
    assert "async def test_" in out


def test_test_use_case_imports_from_usecase_suffixed_module() -> None:
    out = renderer.render_string(_tmpl("use_case/test_use_case.py.jinja2"), _ctx().model_dump())
    assert "from my_app.domain.usecase.create_order_usecase import CreateOrderUseCase" in out


def test_rendered_templates_are_valid_python() -> None:
    for name in ("use_case/use_case.py.jinja2", "use_case/test_use_case.py.jinja2"):
        ast.parse(renderer.render_string(_tmpl(name), _ctx().model_dump()))
