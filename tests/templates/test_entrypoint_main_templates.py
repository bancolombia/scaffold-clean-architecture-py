"""Template rendering tests for entrypoint main.py templates."""

import importlib.resources

from scaffold_ca_python.core.template_renderer import TemplateRenderer
from scaffold_ca_python.models.context import ModuleContext, ProjectContext

renderer = TemplateRenderer()


def _project() -> ProjectContext:
    return ProjectContext(name="my-app")


def _ctx(name: str = "my-app", subtype: str | None = None) -> ModuleContext:
    return ModuleContext(name=name, project=_project())


def _tmpl(name: str) -> str:
    return importlib.resources.files("scaffold_ca_python.templates").joinpath(name).read_text(encoding="utf-8")


def _render(path: str) -> str:
    return renderer.render_string(_tmpl(path), _ctx().model_dump())


def test_default_main_has_def_main() -> None:
    out = _render("project/main.py.jinja2")
    assert "def main" in out


def test_default_main_prints_hello_world() -> None:
    out = _render("project/main.py.jinja2")
    assert "Hello, World!" in out


def test_default_main_has_name_guard() -> None:
    out = _render("project/main.py.jinja2")
    assert '__name__ == "__main__"' in out


def test_agent_main_has_def_main() -> None:
    out = _render("entry_point/agent/entrypoint_main.py.jinja2")
    assert "def main" in out


def test_agent_main_uses_asyncio() -> None:
    out = _render("entry_point/agent/entrypoint_main.py.jinja2")
    assert "asyncio" in out


def test_mcp_main_has_def_main() -> None:
    out = _render("entry_point/mcp/server.py.jinja2")
    assert "def main" in out


def test_mcp_server_uses_asyncio_run() -> None:
    out = _render("entry_point/mcp/server.py.jinja2")
    assert "uvicorn" in out


def test_mcp_main_does_not_use_sys_exit() -> None:
    out = _render("entry_point/mcp/server.py.jinja2")
    assert "sys.exit" not in out


def test_generic_main_has_def_main() -> None:
    out = _render("entry_point/generic/entrypoint_main.py.jinja2")
    assert "def main" in out


def test_generic_main_uses_asyncio() -> None:
    out = _render("entry_point/generic/entrypoint_main.py.jinja2")
    assert "asyncio" in out
