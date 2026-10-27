"""Template rendering tests for entry_point/ group — all 4 types (T087)."""

import ast
import importlib.resources

import pytest

from scaffold_ca_python.core.template_renderer import TemplateRenderer
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from scaffold_ca_python.models.layer import Layer

renderer = TemplateRenderer()


def _project() -> ProjectContext:
    return ProjectContext(name="my-app")


def _ctx(name: str = "my-app", subtype: str | None = None) -> ModuleContext:
    return ModuleContext(name=name, layer=Layer.ENTRY_POINTS, project=_project(), subtype=subtype)


def _tmpl(name: str) -> str:
    return importlib.resources.files("scaffold_ca_python.templates").joinpath(name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# restapi
# ---------------------------------------------------------------------------


def test_entry_point_restapi_rest_controller_has_apirouter() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/rest_controller.py.jinja2"), _ctx().model_dump())
    assert "APIRouter" in out
    assert "async def" in out
    assert "/health" in out


def test_entry_point_restapi_exception_handler_has_http_exception() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/exception_handler.py.jinja2"), _ctx().model_dump())
    assert "HTTPException" in out
    assert "RequestValidationError" in out


def test_entry_point_restapi_server_has_start_server() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/server.py.jinja2"), _ctx().model_dump())
    assert "start_server" in out


# ---------------------------------------------------------------------------
# restapi — server.py thin wrapper (US2 / T011–T012)
# ---------------------------------------------------------------------------


def test_entry_point_restapi_server_is_thin_wrapper() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/server.py.jinja2"), _ctx().model_dump())
    assert "FastAPI" not in out
    assert "Container" not in out


def test_entry_point_restapi_server_imports_start_server() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/server.py.jinja2"), _ctx().model_dump())
    assert "application.app import start_server" in out


# ---------------------------------------------------------------------------
# restapi — app.py template (US1 / T003–T006)
# ---------------------------------------------------------------------------


def test_entry_point_restapi_app_has_create_app_factory() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/app.py.jinja2"), _ctx().model_dump())
    assert "create_app" in out


def test_entry_point_restapi_app_has_lifespan() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/app.py.jinja2"), _ctx().model_dump())
    assert "lifespan" in out
    assert "asynccontextmanager" in out


def test_entry_point_restapi_app_has_container_wiring() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/app.py.jinja2"), _ctx().model_dump())
    assert "Container" in out
    assert "wire(" in out


def test_entry_point_restapi_app_factory_path_uses_application_app() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/app.py.jinja2"), _ctx().model_dump())
    assert "application.app:create_app" in out


# ---------------------------------------------------------------------------
# restapi — test file templates (US4 / T022–T025)
# ---------------------------------------------------------------------------


def test_entry_point_restapi_test_app_template_has_create_app_assertion() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/test_app.py.jinja2"), _ctx().model_dump())
    assert "create_app" in out
    assert "FastAPI" in out


def test_entry_point_restapi_test_server_template_references_start_server() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/test_server.py.jinja2"), _ctx().model_dump())
    assert "start_server" in out


def test_entry_point_restapi_test_exception_handler_template_has_status_codes() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/test_exception_handler.py.jinja2"), _ctx().model_dump())
    assert "422" in out or "HTTPException" in out


# ---------------------------------------------------------------------------
# restapi — test_rest_controller.py template correctness (T004, T005)
# ---------------------------------------------------------------------------


def test_generated_test_rest_controller_imports_application_app() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/test_rest_controller.py.jinja2"), _ctx().model_dump())
    assert "application.app" in out
    assert "server import" not in out


def test_generated_test_rest_controller_has_no_duplicate_docstring() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/test_rest_controller.py.jinja2"), _ctx().model_dump())
    assert out.count('"""Tests') == 1


# ---------------------------------------------------------------------------
# agent
# ---------------------------------------------------------------------------


def test_agent_has_class_name() -> None:
    ctx = _ctx("my-app")
    out = renderer.render_string(_tmpl("entry_point/agent/agent.py.jinja2"), ctx.model_dump())
    assert "Agent" in out


def test_agent_has_async_run() -> None:
    out = renderer.render_string(_tmpl("entry_point/agent/agent.py.jinja2"), _ctx().model_dump())
    assert "async def run" in out


def test_agent_with_kafka_flag_includes_stub() -> None:
    ctx_dict = _ctx().model_dump()
    ctx_dict["enable_kafka"] = True
    out = renderer.render_string(_tmpl("entry_point/agent/agent.py.jinja2"), ctx_dict)
    assert "kafka" in out.lower()


def test_agent_without_kafka_flag_excludes_stub() -> None:
    ctx_dict = _ctx().model_dump()
    ctx_dict["enable_kafka"] = False
    out = renderer.render_string(_tmpl("entry_point/agent/agent.py.jinja2"), ctx_dict)
    assert "AIOKafkaConsumer" not in out


# ---------------------------------------------------------------------------
# mcp — tools.py template (T006)
# ---------------------------------------------------------------------------


def test_mcp_tools_has_bind_tools() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/tools.py.jinja2"), _ctx().model_dump())
    assert "bind_tools" in out


def test_mcp_tools_has_inject_decorator() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/tools.py.jinja2"), _ctx().model_dump())
    assert "@inject" in out


def test_mcp_tools_has_fastmcp_import() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/tools.py.jinja2"), _ctx().model_dump())
    assert "from mcp.server.fastmcp import FastMCP" in out


def test_mcp_tools_is_async() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/tools.py.jinja2"), _ctx().model_dump())
    assert "async def bind_tools" in out


def test_mcp_tools_bind_tools_is_last_statement() -> None:
    """T005: Regression guard — bind_tools must be the last top-level statement.

    The --add-tool feature relies on this invariant: appending to the end of
    tools.py effectively inserts inside bind_tools because bind_tools is always last.
    """
    out = renderer.render_string(_tmpl("entry_point/mcp/tools.py.jinja2"), _ctx().model_dump())
    module = ast.parse(out)
    assert module.body, "tools.py template must have at least one statement"
    last_stmt = module.body[-1]
    assert isinstance(last_stmt, ast.AsyncFunctionDef), "Last statement must be an async function"
    assert last_stmt.name == "bind_tools", "Last function must be named 'bind_tools'"


def test_mcp_tools_contains_nested_example_tool() -> None:
    """T005: Regression guard — bind_tools contains nested @mcp.tool decorator.

    The --add-tool feature appends new tool stubs in the same nested pattern.
    """
    out = renderer.render_string(_tmpl("entry_point/mcp/tools.py.jinja2"), _ctx().model_dump())
    module = ast.parse(out)
    bind_tools_func = module.body[-1]
    assert isinstance(bind_tools_func, ast.AsyncFunctionDef)

    # Find @mcp.tool decorator inside bind_tools
    has_mcp_tool_decorator = False
    for node in ast.walk(bind_tools_func):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "example_tool":
            has_mcp_tool_decorator = True
            break

    assert has_mcp_tool_decorator, "bind_tools must contain nested example_tool function"
    assert '@mcp.tool("example_tool")' in out, "bind_tools must use @mcp.tool decorator"


# ---------------------------------------------------------------------------
# mcp — resources.py template (T007)
# ---------------------------------------------------------------------------


def test_mcp_resources_has_bind_resources() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/resources.py.jinja2"), _ctx().model_dump())
    assert "bind_resources" in out


def test_mcp_resources_has_inject_decorator() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/resources.py.jinja2"), _ctx().model_dump())
    assert "@inject" in out


def test_mcp_resources_has_fastmcp_import() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/resources.py.jinja2"), _ctx().model_dump())
    assert "from mcp.server.fastmcp import FastMCP" in out


def test_mcp_resources_is_async() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/resources.py.jinja2"), _ctx().model_dump())
    assert "async def bind_resources" in out


# ---------------------------------------------------------------------------
# mcp — prompts.py template (T007)
# ---------------------------------------------------------------------------


def test_mcp_prompts_has_bind_prompts() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/prompts.py.jinja2"), _ctx().model_dump())
    assert "bind_prompts" in out


def test_mcp_prompts_has_inject_decorator() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/prompts.py.jinja2"), _ctx().model_dump())
    assert "@inject" in out


def test_mcp_prompts_has_fastmcp_import() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/prompts.py.jinja2"), _ctx().model_dump())
    assert "from mcp.server.fastmcp import FastMCP" in out


def test_mcp_prompts_is_sync_not_async() -> None:
    """bind_prompts is async (same as bind_tools and bind_resources)."""
    out = renderer.render_string(_tmpl("entry_point/mcp/prompts.py.jinja2"), _ctx().model_dump())
    assert "async def bind_prompts" in out


# ---------------------------------------------------------------------------
# mcp — server.py (uvicorn entrypoint) — Phase 4 / T021
# ---------------------------------------------------------------------------


def test_mcp_server_has_main_function() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/server.py.jinja2"), _ctx().model_dump())
    assert "def main" in out


def test_mcp_server_has_uvicorn_run() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/server.py.jinja2"), _ctx().model_dump())
    assert "uvicorn.run" in out


def test_mcp_server_imports_app() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/server.py.jinja2"), _ctx().model_dump())
    assert "import app" in out


# ---------------------------------------------------------------------------
# mcp — app.py (composition root) — Phase 5 / T026–T027
# ---------------------------------------------------------------------------


def _routes_out() -> str:
    return renderer.render_string(_tmpl("entry_point/mcp/routes.py.jinja2"), _ctx().model_dump())


@pytest.mark.parametrize(
    "fragment",
    [
        "from __future__ import annotations",
        "from mcp.server.fastmcp import FastMCP",
        "from starlette.requests import Request",
        "from starlette.responses import JSONResponse, Response",
        "def bind_routes(mcp: FastMCP) -> None:",
        '@mcp.custom_route(name="health_check", path="/api/v1/health", methods=["GET"])',
        "async def health_check(_request: Request) -> Response:",
        '{"status": "ok"}',
        "return JSONResponse(response_data)",
    ],
)
def test_mcp_routes_contains_fragment(fragment: str) -> None:
    assert fragment in _routes_out()


def test_mcp_routes_bind_routes_is_sync_and_not_injected() -> None:
    out = _routes_out()
    assert "async def bind_routes" not in out
    assert "@inject" not in out
    assert "Provide" not in out


def _app_ctx(*, with_resources: bool = False, with_prompts: bool = False) -> dict[str, object]:
    return {**_ctx().model_dump(), "with_resources": with_resources, "with_prompts": with_prompts}


def test_mcp_app_has_fastmcp_instance() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx())
    assert "FastMCP" in out


def test_mcp_app_has_start_server() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx())
    assert "start_server" in out


def test_mcp_app_has_lifespan() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx())
    assert "lifespan" in out
    assert "asynccontextmanager" in out


def test_mcp_app_has_streamable_http_app() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx())
    assert "streamable_http_app" in out


def test_mcp_app_with_resources_includes_bind_resources() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx(with_resources=True))
    assert "bind_resources" in out


def test_mcp_app_without_resources_excludes_bind_resources() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx(with_resources=False))
    assert "bind_resources" not in out


def test_mcp_app_with_prompts_includes_bind_prompts() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx(with_prompts=True))
    assert "bind_prompts" in out


def test_mcp_app_without_prompts_excludes_bind_prompts() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx(with_prompts=False))
    assert "bind_prompts" not in out


# ---------------------------------------------------------------------------
# mcp — test_tools.py template
# ---------------------------------------------------------------------------


def test_mcp_test_tools_has_make_mock_mcp() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_tools.py.jinja2"), _ctx().model_dump())
    assert "_make_mock_mcp" in out


def test_mcp_test_tools_has_registers_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_tools.py.jinja2"), _ctx().model_dump())
    assert "test_bind_tools_registers_example_tool" in out


def test_mcp_test_tools_has_result_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_tools.py.jinja2"), _ctx().model_dump())
    assert "test_example_tool_returns_expected_result" in out


# ---------------------------------------------------------------------------
# mcp — test_resources.py template
# ---------------------------------------------------------------------------


def test_mcp_test_resources_has_make_mock_mcp() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_resources.py.jinja2"), _ctx().model_dump())
    assert "_make_mock_mcp" in out


def test_mcp_test_resources_has_registers_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_resources.py.jinja2"), _ctx().model_dump())
    assert "test_bind_resources_registers_example_resource" in out


def test_mcp_test_resources_has_result_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_resources.py.jinja2"), _ctx().model_dump())
    assert "test_example_resource_returns_dict" in out


# ---------------------------------------------------------------------------
# mcp — test_prompts.py template
# ---------------------------------------------------------------------------


def test_mcp_test_prompts_has_make_mock_mcp() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_prompts.py.jinja2"), _ctx().model_dump())
    assert "_make_mock_mcp" in out


def test_mcp_test_prompts_has_registers_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_prompts.py.jinja2"), _ctx().model_dump())
    assert "test_bind_prompts_registers_example_prompt" in out


def test_mcp_test_prompts_has_result_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_prompts.py.jinja2"), _ctx().model_dump())
    assert "test_example_prompt_returns_expected_string" in out


# ---------------------------------------------------------------------------
# mcp — test_app.py template
# ---------------------------------------------------------------------------


def test_mcp_test_app_has_mcp_instance_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_app.py.jinja2"), _app_ctx())
    assert "test_mcp_instance_is_fastmcp" in out


def test_mcp_test_app_has_start_server_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_app.py.jinja2"), _app_ctx())
    assert "test_start_server_returns_starlette" in out


def test_mcp_test_app_has_routes_test() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_app.py.jinja2"), _app_ctx())
    assert "test_start_server_has_routes" in out


def test_mcp_test_app_imports_fastmcp() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_app.py.jinja2"), _app_ctx())
    assert "FastMCP" in out


# ---------------------------------------------------------------------------
# generic
# ---------------------------------------------------------------------------


def test_generic_has_entry_point_class() -> None:
    out = renderer.render_string(_tmpl("entry_point/generic/handler.py.jinja2"), _ctx().model_dump())
    assert "EntryPoint" in out


def test_generic_has_async_run() -> None:
    out = renderer.render_string(_tmpl("entry_point/generic/handler.py.jinja2"), _ctx().model_dump())
    assert "async def run" in out


# ---------------------------------------------------------------------------
# restapi — test template (US2 / T019)
# ---------------------------------------------------------------------------


def test_entry_point_restapi_test_rest_controller_has_testclient() -> None:
    out = renderer.render_string(_tmpl("entry_point/restapi/test_rest_controller.py.jinja2"), _ctx().model_dump())
    assert "TestClient" in out
    assert "/v1/health" in out
    assert "assert response.status_code == 200" in out


# ---------------------------------------------------------------------------
# mcp — tool_stub.py.jinja2 template (T008)
# ---------------------------------------------------------------------------


def test_tool_stub_template_renders_nested_function_with_decorator() -> None:
    """T008: tool_stub.py.jinja2 renders 4-space-indented nested @mcp.tool function."""
    context = {
        "name": "create_file",
        "params": [
            {"name": "path", "type": "str"},
            {"name": "content", "type": "str"},
        ],
        "returns": "str",
        "docstring": "Creates a file on disk",
    }
    out = renderer.render_string(_tmpl("entry_point/mcp/tool_stub.py.jinja2"), context)

    # Must be 4-space indented (for insertion inside bind_tools)
    assert '    @mcp.tool("create_file")' in out
    assert "    async def create_file(path: str, content: str) -> str:" in out
    assert '        """Creates a file on disk"""' in out
    assert "        raise NotImplementedError(\"Tool 'create_file' is not yet implemented.\")" in out


def test_tool_stub_template_with_no_params() -> None:
    """T008: tool_stub.py.jinja2 renders correctly with zero parameters."""
    context = {
        "name": "list_files",
        "params": [],
        "returns": "list[str]",
        "docstring": "Lists all files",
    }
    out = renderer.render_string(_tmpl("entry_point/mcp/tool_stub.py.jinja2"), context)

    assert '    @mcp.tool("list_files")' in out
    assert "    async def list_files() -> list[str]:" in out
    assert "        raise NotImplementedError(" in out


def test_tool_stub_template_not_wrapped_in_registrar() -> None:
    """T008: tool_stub.py.jinja2 must NOT use @_register_tool or def _bind_."""
    context = {
        "name": "search",
        "params": [{"name": "query", "type": "str"}],
        "returns": "str",
        "docstring": "Search query",
    }
    out = renderer.render_string(_tmpl("entry_point/mcp/tool_stub.py.jinja2"), context)

    assert "@_register_tool" not in out
    assert "def _bind_" not in out


# ---------------------------------------------------------------------------
# mcp — test_tool_stub.py.jinja2 template (T008)
# ---------------------------------------------------------------------------


def test_test_tool_stub_template_renders_registration_test() -> None:
    """T008: test_tool_stub.py.jinja2 renders registration assertion test."""
    context = {"name": "create_file"}
    out = renderer.render_string(_tmpl("entry_point/mcp/test_tool_stub.py.jinja2"), context)

    # Must be a top-level function (not indented)
    assert "def test_bind_tools_registers_create_file() -> None:" in out
    assert '"create_file" in registered' in out or "'create_file' in registered" in out
    assert "_make_mock_mcp()" in out


def test_test_tool_stub_template_does_not_call_tool() -> None:
    """T008: test_tool_stub.py.jinja2 must NOT call/await the tool itself."""
    context = {"name": "do_action"}
    out = renderer.render_string(_tmpl("entry_point/mcp/test_tool_stub.py.jinja2"), context)

    # Should only check registration, not invoke the tool
    assert "registered[" not in out or 'await registered["do_action"]' not in out
    assert "do_action(" not in out or "await do_action(" not in out


# ---------------------------------------------------------------------------
# mcp — health route wiring and tests (027)
# ---------------------------------------------------------------------------

_APP_COMBOS = [(r, p) for r in (False, True) for p in (False, True)]


@pytest.mark.parametrize(("with_resources", "with_prompts"), _APP_COMBOS)
def test_mcp_app_binds_routes_once_after_mcp_creation(with_resources: bool, with_prompts: bool) -> None:
    out = renderer.render_string(
        _tmpl("entry_point/mcp/app.py.jinja2"), _app_ctx(with_resources=with_resources, with_prompts=with_prompts)
    )
    assert "mcp_server import routes, tools" in out
    assert out.count("routes.bind_routes(mcp)") == 1
    call = out.index("routes.bind_routes(mcp)")
    assert out.index("mcp: FastMCP = FastMCP(") < call < out.index("async def lifespan")
    assert call < out.index("def start_server")
    wire_block = out[out.index("container.wire(") : out.index("await tools.bind_tools")]
    assert "routes" not in wire_block
    assert ("bind_resources" in out) is with_resources
    assert ("bind_prompts" in out) is with_prompts


def test_mcp_test_routes_template() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_routes.py.jinja2"), _ctx().model_dump())
    assert "from my_app.infrastructure.entry_points.mcp_server.routes import bind_routes" in out
    assert "from starlette.testclient import TestClient" in out
    assert "FastMCP(" in out
    assert "bind_routes(" in out
    assert '.get("/api/v1/health")' in out
    assert "== 200" in out
    assert '{"status": "ok"}' in out
    assert '.post("/api/v1/health")' in out
    assert "== 405" in out
    assert "with TestClient" not in out
    assert "application.app" not in out


def test_mcp_test_app_health_tests() -> None:
    out = renderer.render_string(_tmpl("entry_point/mcp/test_app.py.jinja2"), _app_ctx())
    assert "def test_health_route_registered_once" in out
    assert out.count("start_server()") >= 3
    assert "== 1" in out
    assert "def test_health_route_reachable_through_start_server" in out
    assert "TestClient(app_module.start_server())" in out
    assert "with TestClient" not in out
