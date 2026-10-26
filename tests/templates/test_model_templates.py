"""Template rendering tests for model/ group (T084)."""

import importlib.resources

from scaffold_ca_python.core.template_renderer import TemplateRenderer
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from scaffold_ca_python.models.layer import Layer

renderer = TemplateRenderer()


def _project() -> ProjectContext:
    return ProjectContext(name="my-app")


def _ctx() -> ModuleContext:
    return ModuleContext(name="order", layer=Layer.DOMAIN_MODEL, project=_project())


def _tmpl(name: str) -> str:
    return importlib.resources.files("scaffold_ca_python.templates").joinpath(name).read_text(encoding="utf-8")


def test_model_class_name_present() -> None:
    ctx = _ctx()
    out = renderer.render_string(_tmpl("model/model.py.jinja2"), ctx.model_dump())
    assert "Order" in out


def test_model_has_base_model_import() -> None:
    out = renderer.render_string(_tmpl("model/model.py.jinja2"), _ctx().model_dump())
    assert "BaseModel" in out


def test_model_class_inherits_base_model() -> None:
    out = renderer.render_string(_tmpl("model/model.py.jinja2"), _ctx().model_dump())
    assert "class Order(BaseModel)" in out


def test_test_model_imports_class() -> None:
    out = renderer.render_string(_tmpl("model/test_model.py.jinja2"), _ctx().model_dump())
    assert "Order" in out


def test_gateway_is_empty_abc_without_model_import() -> None:
    out = renderer.render_string(_tmpl("model/gateway.py.jinja2"), _ctx().model_dump())
    assert "from abc import ABC" in out
    assert "class OrderRepository(ABC):" in out
    assert "domain.model" not in out
    assert "BaseModel" not in out
    assert "def " not in out


def test_gateway_test_imports_and_asserts_abc() -> None:
    out = renderer.render_string(_tmpl("model/test_gateway.py.jinja2"), _ctx().model_dump())
    assert "from my_app.domain.model.order.gateways.order_repository import OrderRepository" in out
    assert "issubclass(OrderRepository, ABC)" in out


def test_package_init_templates_have_docstring() -> None:
    for name in ("model/__init__.py.jinja2", "model/gateways_init.py.jinja2"):
        out = renderer.render_string(_tmpl(name), _ctx().model_dump())
        assert "Order" in out
        assert out.lstrip().startswith('"""')


def test_test_model_imports_from_package_path() -> None:
    out = renderer.render_string(_tmpl("model/test_model.py.jinja2"), _ctx().model_dump())
    assert "from my_app.domain.model.order.order import Order" in out
