"""Template rendering tests for DI config templates (wireup, 028)."""

import importlib.resources

from scaffold_ca_python.core.template_renderer import TemplateRenderer
from scaffold_ca_python.models.context import ProjectContext

renderer = TemplateRenderer()


def _ctx() -> ProjectContext:
    return ProjectContext(name="order-service")


def _tmpl(name: str) -> str:
    return importlib.resources.files("scaffold_ca_python.templates").joinpath(name).read_text(encoding="utf-8")


def _render(filename: str) -> str:
    return renderer.render_string(
        _tmpl(f"project/application/config/{filename}.jinja2"),
        _ctx().model_dump(),
    )


# --- __init__.py -----------------------------------------------------------


def test_init_renders() -> None:
    out = _render("__init__.py")
    assert out is not None


# --- config.py -------------------------------------------------------------


def test_config_has_settings_class() -> None:
    out = _render("config.py")
    assert "Settings" in out


def test_config_has_base_settings() -> None:
    out = _render("config.py")
    assert "BaseSettings" in out


def test_config_has_settings_singleton() -> None:
    out = _render("config.py")
    assert "settings = Settings()" in out


# --- wiring.py (wireup) ---------------------------------------------------


def test_wiring_has_injectables() -> None:
    """FR-001: wiring.py must define INJECTABLES list."""
    out = _render("wiring.py")
    assert "INJECTABLES" in out


def test_wiring_has_create_container() -> None:
    """FR-001: wiring.py must define create_container() function."""
    out = _render("wiring.py")
    assert "create_container" in out


def test_wiring_calls_create_async_container() -> None:
    """FR-001, D2: wiring.py must call wireup.create_async_container (async-first)."""
    out = _render("wiring.py")
    assert "create_async_container" in out


def test_wiring_no_dependency_injector_imports() -> None:
    """FR-001: wiring.py must not import dependency-injector."""
    out = _render("wiring.py")
    assert "dependency_injector" not in out
    assert "DependenciesContainer" not in out


def test_wiring_imports_driven_adapters() -> None:
    """FR-001: wiring.py must import driven_adapters package for scan."""
    ctx = _ctx()
    out = renderer.render_string(
        _tmpl("project/application/config/wiring.py.jinja2"),
        ctx.model_dump(),
    )
    assert "driven_adapters" in out
    assert ctx.python_package in out


def test_wiring_imports_helpers() -> None:
    """FR-001: wiring.py must import helpers package for scan."""
    out = _render("wiring.py")
    assert "helpers" in out


def test_wiring_imports_usecases() -> None:
    """FR-004: wiring.py must import usecases package for scan."""
    out = _render("wiring.py")
    assert "usecases" in out


# --- usecases/__init__.py -------------------------------------------------


def test_usecases_init_renders() -> None:
    """FR-004: usecases/__init__.py must be generated (package marker for wireup)."""
    out = renderer.render_string(
        _tmpl("project/application/config/usecases/__init__.py.jinja2"),
        _ctx().model_dump(),
    )
    assert out is not None


# --- US3 (T042-T046): Fail-fast validation --------------------------------


def test_restapi_app_lifespan_warms_container() -> None:
    """T046: restapi app.py lifespan must create container before yielding."""
    content = (
        importlib.resources.files("scaffold_ca_python.templates")
        .joinpath("entry_point/restapi/app.py.jinja2")
        .read_text(encoding="utf-8")
    )
    # Must create container and call setup before yield
    assert "create_container()" in content
    assert "wireup.integration.fastapi.setup" in content
    # Verify lifespan exists and is async
    assert "async def lifespan" in content
    assert "yield" in content


def test_mcp_app_lifespan_warms_container() -> None:
    """T045: mcp app.py lifespan must warm up container before yielding."""
    content = (
        importlib.resources.files("scaffold_ca_python.templates")
        .joinpath("entry_point/mcp/app.py.jinja2")
        .read_text(encoding="utf-8")
    )
    # Must create container and inject dependencies before yielding
    assert "create_container()" in content
    assert "inject_from_container" in content
    # Verify lifespan exists and is async
    assert "async def lifespan" in content or "asynccontextmanager" in content
    assert "yield" in content


def test_agent_app_creates_container() -> None:
    """T035: agent app.py must create container in composition root."""
    content = (
        importlib.resources.files("scaffold_ca_python.templates")
        .joinpath("entry_point/agent/agent_app.py.jinja2")
        .read_text(encoding="utf-8")
    )
    assert "create_container()" in content
    assert "asynccontextmanager" in content
    assert "yield" in content


def test_generic_app_creates_container() -> None:
    """T037: generic app.py must create container in composition root."""
    content = (
        importlib.resources.files("scaffold_ca_python.templates")
        .joinpath("entry_point/generic/generic_app.py.jinja2")
        .read_text(encoding="utf-8")
    )
    assert "create_container()" in content
    assert "asynccontextmanager" in content
    assert "yield" in content
