"""Tests for gep / generate-entry-point command (T050)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.conftest import strip_ansi

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bootstrap a minimal CA project root inside tmp_path."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    return project_dir


@pytest.fixture()
def mcp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bootstrap a project with an MCP entry point (T004).

    Creates a CA project and generates the MCP server infrastructure,
    ready for --add-tool tests.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    return project_dir


@pytest.fixture()
def swagger_file(tmp_path: Path) -> Path:
    """A minimal valid OpenAPI YAML file for --swagger tests."""
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        "openapi: '3.0.0'\n"
        "info:\n"
        "  title: Test API\n"
        "  version: '1.0.0'\n"
        "paths:\n"
        "  /users:\n"
        "    get:\n"
        "      summary: List users\n"
        "      responses:\n"
        "        '200':\n"
        "          description: OK\n"
        "  /orders:\n"
        "    post:\n"
        "      summary: Create order\n"
        "      responses:\n"
        "        '201':\n"
        "          description: Created\n"
    )
    return spec_path


# ---------------------------------------------------------------------------
# restapi type
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# US1 — application/app.py emitted (T002)
# ---------------------------------------------------------------------------


def test_restapi_creates_app_py(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "application" / "app.py").exists()


# ---------------------------------------------------------------------------
# US2 — server.py is thin wrapper (T010)
# ---------------------------------------------------------------------------


def test_restapi_server_py_is_thin_wrapper(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0
    content = (project_root / "src" / "my_app" / "server.py").read_text()
    assert "FastAPI" not in content
    meaningful_lines = [ln for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert len(meaningful_lines) <= 5


# ---------------------------------------------------------------------------
# US3 — no main.py emitted for restapi (T015, T016, T016c)
# ---------------------------------------------------------------------------


def test_restapi_no_main_py(project_root: Path) -> None:
    # main.py is created by scaffold ca; gep --type restapi must not create it if absent
    (project_root / "src" / "my_app" / "main.py").unlink(missing_ok=True)
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert not (project_root / "src" / "my_app" / "main.py").exists()


def test_restapi_dry_run_includes_app_py_not_main(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "app.py" in result.output
    # main.py must not appear as a *created* file — it appears as a deletion notice (FR-004)
    assert "Would delete" in result.output
    # dry-run must NOT actually delete the file
    assert (project_root / "src" / "my_app" / "main.py").exists()


def test_restapi_gep_twice_does_not_overwrite_app_py(project_root: Path) -> None:
    import shutil

    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    app_py = project_root / "src" / "my_app" / "application" / "app.py"
    original_content = app_py.read_text()

    # Clean up so gep can run a second time
    shutil.rmtree(project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api")
    shutil.rmtree(project_root / "src" / "tests" / "infrastructure" / "entry_points" / "api", ignore_errors=True)
    (project_root / "src" / "my_app" / "server.py").unlink(missing_ok=True)
    (project_root / "src" / "tests" / "application" / "test_app.py").unlink(missing_ok=True)
    app_py.unlink(missing_ok=True)

    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert app_py.read_text() == original_content


# ---------------------------------------------------------------------------
# US4 — test files emitted by gep --type restapi (T018–T021)
# ---------------------------------------------------------------------------


def test_restapi_creates_test_app(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert (project_root / "src" / "tests" / "application" / "test_app.py").exists()


def test_restapi_creates_test_server(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert (
        project_root / "src" / "tests" / "infrastructure" / "entry_points" / "api" / "v1" / "test_server.py"
    ).exists()


def test_restapi_creates_test_exception_handler(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert (
        project_root / "src" / "tests" / "infrastructure" / "entry_points" / "api" / "v1" / "test_exception_handler.py"
    ).exists()


# ---------------------------------------------------------------------------
# Existing file-existence tests
# ---------------------------------------------------------------------------


def test_restapi_creates_init(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api" / "v1" / "__init__.py").exists()


def test_restapi_creates_rest_controller(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (
        project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api" / "v1" / "rest_controller.py"
    ).exists()


def test_restapi_creates_exception_handler(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (
        project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api" / "v1" / "exception_handler.py"
    ).exists()


def test_restapi_creates_server_py(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "server.py").exists()


def test_restapi_creates_test(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (
        project_root / "src" / "tests" / "infrastructure" / "entry_points" / "api" / "v1" / "test_rest_controller.py"
    ).exists()


def test_restapi_main_contains_fastapi(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    content = (
        project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api" / "v1" / "rest_controller.py"
    ).read_text()
    assert "FastAPI" in content or "APIRouter" in content


def test_restapi_dry_run_lists_all_planned_files_and_writes_nothing(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "rest_controller.py" in result.output
    assert "exception_handler.py" in result.output
    assert "server.py" in result.output
    assert not (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api").exists()


# ---------------------------------------------------------------------------
# restapi + --swagger
# ---------------------------------------------------------------------------


def test_swagger_injects_routes(project_root: Path, swagger_file: Path) -> None:
    result = runner.invoke(
        app,
        ["gep", "--type", "restapi", "--swagger", str(swagger_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# agent type
# ---------------------------------------------------------------------------


def test_agent_creates_init(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "agent" / "__init__.py").exists()


def test_agent_creates_agent_file(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "agent" / "agent.py").exists()


def test_agent_creates_card_file(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "agent" / "card.py").exists()


def test_agent_creates_test(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "tests" / "infrastructure" / "entry_points" / "agent" / "test_agent.py").exists()


def test_agent_with_enable_kafka(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent", "--enable-kafka"], catch_exceptions=False)
    assert result.exit_code == 0
    content = (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "agent" / "agent.py").read_text()
    assert "kafka" in content.lower() or "Kafka" in content


def test_agent_with_enable_mcp_client(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent", "--enable-mcp-client"], catch_exceptions=False)
    assert result.exit_code == 0
    content = (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "agent" / "agent.py").read_text()
    assert "mcp" in content.lower() or "MCP" in content


# ---------------------------------------------------------------------------
# mcp type
# ---------------------------------------------------------------------------


def test_mcp_creates_init(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "__init__.py").exists()


def test_mcp_creates_tools_py(project_root: Path) -> None:
    """T009: base mcp run creates tools.py (replacing old monolithic server.py)."""
    result = runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py").exists()


def test_mcp_no_monolithic_server_py_in_mcp_server(project_root: Path) -> None:
    """T009: old monolithic server.py must NOT exist inside mcp_server/ after restructure."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    server_py = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "server.py"
    assert not server_py.exists()


def test_mcp_creates_test_tools(project_root: Path) -> None:
    """T009: base mcp run creates test_tools.py (replacing old test_server.py)."""
    result = runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (
        project_root / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"
    ).exists()


def test_mcp_with_resources_creates_resources_py(project_root: Path) -> None:
    """T009: --with-resources creates resources.py in mcp_server/."""
    result = runner.invoke(app, ["gep", "--type", "mcp", "--with-resources"], catch_exceptions=False)
    assert result.exit_code == 0
    resources_py = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "resources.py"
    assert resources_py.exists()


def test_mcp_with_resources_creates_test_resources_py(project_root: Path) -> None:
    """T009: --with-resources also creates test_resources.py."""
    result = runner.invoke(app, ["gep", "--type", "mcp", "--with-resources"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (
        project_root / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_resources.py"
    ).exists()


def test_mcp_without_resources_no_resources_py(project_root: Path) -> None:
    """T009: without --with-resources no resources.py is created."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    resources_py = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "resources.py"
    assert not resources_py.exists()


def test_mcp_with_prompts_creates_prompts_py(project_root: Path) -> None:
    """T009: --with-prompts creates prompts.py in mcp_server/."""
    result = runner.invoke(app, ["gep", "--type", "mcp", "--with-prompts"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "prompts.py").exists()


def test_mcp_with_prompts_creates_test_prompts_py(project_root: Path) -> None:
    """T009: --with-prompts also creates test_prompts.py."""
    result = runner.invoke(app, ["gep", "--type", "mcp", "--with-prompts"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (
        project_root / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_prompts.py"
    ).exists()


def test_mcp_without_prompts_no_prompts_py(project_root: Path) -> None:
    """T009: without --with-prompts no prompts.py is created."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    prompts_py = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "prompts.py"
    assert not prompts_py.exists()


def test_mcp_with_all_flags_creates_all_primitive_files(project_root: Path) -> None:
    """T009 / SC-002: --with-resources --with-prompts generates all three primitive files."""
    result = runner.invoke(app, ["gep", "--type", "mcp", "--with-resources", "--with-prompts"], catch_exceptions=False)
    assert result.exit_code == 0
    mcp_dir = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server"
    assert (mcp_dir / "tools.py").exists()
    assert (mcp_dir / "resources.py").exists()
    assert (mcp_dir / "prompts.py").exists()


def test_mcp_flags_rejected_for_restapi_type(project_root: Path) -> None:
    """T009 / FR-012: --with-resources with non-mcp type exits 1 with hint."""
    result = runner.invoke(app, ["gep", "--type", "restapi", "--with-resources"])
    assert result.exit_code == 1
    assert "only valid with --type mcp" in result.output


def test_mcp_prompts_flag_rejected_for_agent_type(project_root: Path) -> None:
    """T009 / FR-012: --with-prompts with non-mcp type exits 1 with hint."""
    result = runner.invoke(app, ["gep", "--type", "agent", "--with-prompts"])
    assert result.exit_code == 1
    assert "only valid with --type mcp" in result.output


# ---------------------------------------------------------------------------
# generic type
# ---------------------------------------------------------------------------


def test_generic_creates_init(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "generic" / "__init__.py").exists()


def test_generic_creates_handler(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "generic" / "entry_point.py").exists()


def test_generic_creates_test(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (
        project_root / "src" / "tests" / "infrastructure" / "entry_points" / "generic" / "test_entry_point.py"
    ).exists()


# ---------------------------------------------------------------------------
# Alias
# ---------------------------------------------------------------------------


def test_generate_entry_point_alias_works(project_root: Path) -> None:
    result = runner.invoke(app, ["generate-entry-point", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (
        project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api" / "v1" / "rest_controller.py"
    ).exists()


def test_dry_run_prints_paths(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert "api" in result.output or "v1" in result.output or "server.py" in result.output


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_unknown_type_exits_1(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "graphql"])
    assert result.exit_code == 1
    assert "graphql" in result.output.lower() or "Unknown" in result.output


def test_swagger_without_restapi_exits_1(project_root: Path, swagger_file: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent", "--swagger", str(swagger_file)])
    assert result.exit_code == 1
    assert "--swagger" in result.output


def test_swagger_missing_file_exits_1(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--swagger", "/nonexistent/spec.yaml"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "spec.yaml" in result.output


def test_enable_mcp_client_with_mcp_type_exits_1(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "mcp", "--enable-mcp-client"])
    assert result.exit_code == 1
    assert "--enable-mcp-client" in result.output


def test_duplicate_entry_point_exits_1(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "restapi"])
    assert result.exit_code == 1


def test_no_project_root_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["gep", "--type", "restapi"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# US3: main.py overwritten (agent / mcp / generic only)
# ---------------------------------------------------------------------------


def test_agent_overwrites_main_py(project_root: Path) -> None:
    main_py = project_root / "src" / "my_app" / "main.py"
    runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    content = main_py.read_text()
    assert "def main" in content
    assert "asyncio" in content


def test_mcp_overwrites_main_py(project_root: Path) -> None:
    """Phase 4 / T025: gep --type mcp writes server.py at the package root.

    When T025 is implemented, ep_mcp.py will:
      - add server.py.jinja2 at <pkg>/server.py (uvicorn entrypoint)
      - set scripts_entry=True so pyproject.toml [project.scripts] is updated

    Until then this test must remain xfail (strict) so it is visible as a
    Phase 4 obligation.
    """
    server_py = project_root / "src" / "my_app" / "server.py"
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    assert server_py.exists(), "server.py must exist after gep --type mcp (Phase 4)"
    content = server_py.read_text()
    assert "uvicorn" in content


def test_generic_overwrites_main_py(project_root: Path) -> None:
    main_py = project_root / "src" / "my_app" / "main.py"
    runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    content = main_py.read_text()
    assert "def main" in content
    assert "asyncio" in content


def test_dry_run_does_not_create_main_py(project_root: Path) -> None:
    # gep --type restapi never creates main.py, even in real run — confirm dry-run also skips it
    (project_root / "src" / "my_app" / "main.py").unlink(missing_ok=True)
    runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert not (project_root / "src" / "my_app" / "main.py").exists()


# ---------------------------------------------------------------------------
# US4: Auto-inject dependencies
# ---------------------------------------------------------------------------


def test_restapi_injects_fastapi_and_uvicorn(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    content = (project_root / "pyproject.toml").read_text()
    assert "fastapi" in content
    assert "uvicorn" in content


def test_agent_injects_a2a_sdk(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    content = (project_root / "pyproject.toml").read_text()
    assert "a2a-sdk" in content


def test_mcp_injects_mcp(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    content = (project_root / "pyproject.toml").read_text()
    assert "mcp" in content


def test_restapi_inject_is_idempotent(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    # Remove both src and test dirs, server.py, app.py, and test_app.py so gep can execute a second time
    import shutil

    shutil.rmtree(project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api")
    shutil.rmtree(project_root / "src" / "tests" / "infrastructure" / "entry_points" / "api", ignore_errors=True)
    (project_root / "src" / "my_app" / "server.py").unlink(missing_ok=True)
    (project_root / "src" / "my_app" / "application" / "app.py").unlink(missing_ok=True)
    (project_root / "src" / "tests" / "application" / "test_app.py").unlink(missing_ok=True)
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    content = (project_root / "pyproject.toml").read_text()
    assert content.count("fastapi") == 1


def test_dry_run_does_not_inject_deps(project_root: Path) -> None:
    original = (project_root / "pyproject.toml").read_text()
    runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert (project_root / "pyproject.toml").read_text() == original


def test_dry_run_prints_deps_to_inject(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert "fastapi" in result.output or "uvicorn" in result.output


# ---------------------------------------------------------------------------
# SC-005 / FR-015: Idempotency integration test (T042)
# ---------------------------------------------------------------------------


def test_gep_restapi_twice_has_exactly_one_fastapi_entry(project_root: Path) -> None:
    """Running gep --type restapi twice must not duplicate fastapi in pyproject.toml."""
    import shutil

    # First run
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    # Remove generated dirs so gep can run again without hitting the duplicate guard
    shutil.rmtree(project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api")
    shutil.rmtree(
        project_root / "src" / "tests" / "infrastructure" / "entry_points" / "api",
        ignore_errors=True,
    )
    (project_root / "src" / "my_app" / "server.py").unlink(missing_ok=True)
    (project_root / "src" / "my_app" / "application" / "app.py").unlink(missing_ok=True)
    (project_root / "src" / "tests" / "application" / "test_app.py").unlink(missing_ok=True)
    # Second run
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)

    content = (project_root / "pyproject.toml").read_text()
    assert content.count("fastapi") == 1


# ---------------------------------------------------------------------------
# US2: gep --help epilog
# ---------------------------------------------------------------------------


def test_gep_help_shows_type_descriptions() -> None:
    result = runner.invoke(app, ["gep", "--help"])
    assert result.exit_code == 0
    assert "FastAPI" in result.output


def test_gep_help_contains_examples_section() -> None:
    result = runner.invoke(app, ["gep", "--help"])
    assert result.exit_code == 0
    assert "Examples" in result.output


# ---------------------------------------------------------------------------
# US3: no-args → help (T019)
# ---------------------------------------------------------------------------


def test_gep_no_args_exits_0() -> None:
    result = runner.invoke(app, ["gep"])
    assert result.exit_code == 0


def test_gep_no_args_shows_type_option() -> None:
    result = runner.invoke(app, ["gep"])
    assert "--type" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# US3 (feature 008): compatibility guard — T005/T006/T007/T008
# ---------------------------------------------------------------------------


def test_gep_restapi_blocked_when_mcp_server_exists(
    project_root: Path,
) -> None:
    """FR-009: exit 1 when mcp_server/ dir already exists; no api/v1/ created."""
    conflict = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server"
    conflict.mkdir(parents=True)

    result = runner.invoke(app, ["gep", "--type", "restapi"])

    assert result.exit_code == 1
    assert not (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api").exists()
    assert "mcp_server" in result.output


def test_gep_restapi_blocked_when_agent_exists(
    project_root: Path,
) -> None:
    """FR-010: exit 1 when agent/ dir already exists; no api/v1/ created."""
    conflict = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "agent"
    conflict.mkdir(parents=True)

    result = runner.invoke(app, ["gep", "--type", "restapi"])

    assert result.exit_code == 1
    assert not (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api").exists()
    assert "agent" in result.output


def test_gep_restapi_proceeds_when_no_incompatible_entry_point(
    project_root: Path,
) -> None:
    """FR-009/FR-010: clean project — guard must NOT block generation."""
    result = runner.invoke(app, ["gep", "--type", "restapi"])

    assert result.exit_code == 0


def test_gep_restapi_dry_run_still_reports_mcp_conflict(
    project_root: Path,
) -> None:
    """FR-013: --dry-run does not bypass the compatibility guard."""
    conflict = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server"
    conflict.mkdir(parents=True)

    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"])

    assert result.exit_code == 1
    assert not (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api").exists()
    assert "mcp_server" in result.output


# ---------------------------------------------------------------------------
# Feature 011 — US1: gep --type restapi deletes main.py (FR-001)
# ---------------------------------------------------------------------------


def test_restapi_deletes_main_py(project_root: Path) -> None:
    """T010: main.py created by scaffold ca must be removed after gep --type restapi."""
    main_py = project_root / "src" / "my_app" / "main.py"
    assert main_py.exists(), "fixture must create main.py via scaffold ca"
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert not main_py.exists()


def test_restapi_second_run_exits_with_duplicate_error(project_root: Path) -> None:
    """T010b: second gep --type restapi must fail on duplicate guard; main.py still absent."""
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    main_py = project_root / "src" / "my_app" / "main.py"
    # Second run — duplicate guard fires because src_dir already exists
    result = runner.invoke(app, ["gep", "--type", "restapi"])
    assert result.exit_code != 0
    assert not main_py.exists()


def test_restapi_gep_ok_when_main_py_already_absent(project_root: Path) -> None:
    """T011: silent no-op delete — command must succeed even if main.py is already gone."""
    (project_root / "src" / "my_app" / "main.py").unlink(missing_ok=True)
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0


def test_restapi_dry_run_reports_would_delete_main_py(project_root: Path) -> None:
    """T012: dry-run must mention main.py in output; the file must NOT be deleted."""
    main_py = project_root / "src" / "my_app" / "main.py"
    assert main_py.exists()
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "main.py" in result.output
    assert main_py.exists()


# ---------------------------------------------------------------------------
# Feature 011 — US2: gep --type restapi updates [project.scripts] (FR-002)
# ---------------------------------------------------------------------------


def test_restapi_updates_project_scripts(project_root: Path) -> None:
    """T015: [project.scripts] entry must read <pkg>.server:start_server after gep restapi."""
    import tomllib

    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.server:start_server"


def test_restapi_dry_run_reports_scripts_update(project_root: Path) -> None:
    """T016: dry-run reports the scripts update; pyproject.toml must remain unchanged."""
    import tomllib

    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "server:start_server" in result.output
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.main:main"


def test_agent_does_not_change_project_scripts(project_root: Path) -> None:
    """T017: gep --type agent must NOT modify [project.scripts]."""
    import tomllib

    runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.main:main"


def test_mcp_updates_pyproject_scripts_to_server_main(project_root: Path) -> None:
    """Phase 4 / T023: gep --type mcp must update [project.scripts] to <pkg>.server:main."""
    import tomllib

    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.server:main"


def test_mcp_creates_server_py_at_package_root(project_root: Path) -> None:
    """Phase 4 / T023: gep --type mcp must create server.py at <pkg> root."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    server_py = project_root / "src" / "my_app" / "server.py"
    assert server_py.exists(), "server.py must be created at the package root"
    assert "uvicorn" in server_py.read_text()


def test_mcp_deletes_main_py(project_root: Path) -> None:
    """Phase 4 / T023: gep --type mcp must delete main.py after creating server.py."""
    main_py = project_root / "src" / "my_app" / "main.py"
    assert main_py.exists(), "fixture must provide main.py"
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    assert not main_py.exists(), "main.py must be deleted after gep --type mcp"


def test_generic_does_not_change_project_scripts(project_root: Path) -> None:
    """T018b: gep --type generic must NOT modify [project.scripts]."""
    import tomllib

    runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.main:main"


# ---------------------------------------------------------------------------
# Bidirectional exclusivity — restapi <-> mcp/agent (T024-T026)
# ---------------------------------------------------------------------------


def test_gep_mcp_blocked_when_restapi_exists(project_root: Path) -> None:
    """T024: mcp must be blocked when restapi entry point already exists."""
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "mcp"])
    assert result.exit_code == 1
    assert "restapi" in result.output


def test_gep_agent_blocked_when_restapi_exists(project_root: Path) -> None:
    """T025: agent must be blocked when restapi entry point already exists."""
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "agent"])
    assert result.exit_code == 1
    assert "restapi" in result.output


def test_gep_generic_not_blocked_when_restapi_exists(project_root: Path) -> None:
    """T026: generic is always allowed regardless of existing entry points."""
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Phase 5 / T029 — application/app.py composition root (US3)
# ---------------------------------------------------------------------------


def test_mcp_creates_app_py(project_root: Path) -> None:
    """T029: gep --type mcp must create application/app.py."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    app_py = project_root / "src" / "my_app" / "application" / "app.py"
    assert app_py.exists(), "application/app.py must be created by gep --type mcp"


def test_mcp_app_py_with_resources_contains_bind_resources(project_root: Path) -> None:
    """T029: gep --type mcp --with-resources must include bind_resources in app.py."""
    runner.invoke(app, ["gep", "--type", "mcp", "--with-resources"], catch_exceptions=False)
    app_py = project_root / "src" / "my_app" / "application" / "app.py"
    assert app_py.exists()
    assert "bind_resources" in app_py.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 3 / T017 — User Story 1: --add-tool happy path
# ---------------------------------------------------------------------------


def test_add_tool_full_flag_invocation(mcp_project: Path) -> None:
    """T017(1): Full-flag --add-tool invocation inserts correctly-shaped stub."""
    result = runner.invoke(
        app,
        [
            "gep",
            "--type",
            "mcp",
            "--add-tool",
            "--name",
            "create_file",
            "--param",
            "path:str",
            "--param",
            "content:str",
            "--returns",
            "str",
            "--description",
            "Creates a file on disk",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text(encoding="utf-8")

    # Check stub is present with correct signature
    assert '@mcp.tool("create_file")' in content
    assert "async def create_file(path: str, content: str) -> str:" in content
    assert '"Creates a file on disk"' in content or "'Creates a file on disk'" in content
    assert "NotImplementedError" in content


def test_add_tool_zero_params(mcp_project: Path) -> None:
    """T017(2): Zero --param flags produce stub with no extra parameters."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "list_files"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text(encoding="utf-8")

    assert '@mcp.tool("list_files")' in content
    assert "async def list_files() -> str:" in content


def test_add_tool_defaults_returns_and_description(mcp_project: Path) -> None:
    """T017(3): Omitted --returns/--description use defaults."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "get_status"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text(encoding="utf-8")

    # Default return type is str
    assert "async def get_status() -> str:" in content
    # Default description is a placeholder
    assert "TODO" in content or "describe this tool" in content


def test_add_tool_preserves_existing_tools(mcp_project: Path) -> None:
    """T017(4): Pre-existing example_tool and its tests remain unchanged."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    test_tools_py = mcp_project / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"

    # Add a new tool
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "new_tool"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    # Check example_tool still exists
    new_tools = tools_py.read_text(encoding="utf-8")
    assert "example_tool" in new_tools
    assert '@mcp.tool("example_tool")' in new_tools

    # Check test for example_tool still exists
    new_tests = test_tools_py.read_text(encoding="utf-8")
    assert "test_bind_tools_registers_example_tool" in new_tests


def test_add_tool_creates_registration_test(mcp_project: Path) -> None:
    """T017(5): test_tools.py gains registration test that passes."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    test_tools_py = mcp_project / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"
    content = test_tools_py.read_text(encoding="utf-8")

    # Check test was added
    assert "test_bind_tools_registers_create_file" in content
    assert '"create_file" in registered' in content or "'create_file' in registered" in content

    # Run the tests in the generated project (disable coverage for this subprocess test)
    import subprocess

    # First, install dependencies in the generated project
    sync_result = subprocess.run(
        ["uv", "sync", "--no-progress"],
        cwd=mcp_project,
        capture_output=True,
        text=True,
        timeout=60,  # 60 second timeout for sync
    )

    # If sync fails, it means we can't verify the test runs, but the test generation itself is valid
    # This can happen in CI with network issues or package availability problems
    if sync_result.returncode != 0:
        pytest.skip(f"Cannot run generated tests: uv sync failed: {sync_result.stderr}")

    result = subprocess.run(
        ["uv", "run", "pytest", str(test_tools_py), "-v", "--no-cov"],
        cwd=mcp_project,
        capture_output=True,
        text=True,
        timeout=30,  # 30 second timeout for pytest
    )
    assert result.returncode == 0, f"Generated tests failed: {result.stdout}\n{result.stderr}"


def test_add_tool_only_modifies_tools_and_tests(mcp_project: Path) -> None:
    """T017(6): Only tools.py and test_tools.py are modified, no other files."""
    # Take snapshot before
    before_files = {p.relative_to(mcp_project): p.read_bytes() for p in mcp_project.rglob("*") if p.is_file()}

    # Add tool
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    # Take snapshot after
    after_files = {p.relative_to(mcp_project): p.read_bytes() for p in mcp_project.rglob("*") if p.is_file()}

    # Find changed files
    changed = set()
    for path in before_files.keys() | after_files.keys():
        if before_files.get(path) != after_files.get(path):
            changed.add(str(path))

    # Should only have changed tools.py and test_tools.py
    expected_changes = {
        "src/my_app/infrastructure/entry_points/mcp_server/tools.py",
        "src/tests/infrastructure/entry_points/mcp_server/test_tools.py",
    }

    assert changed == expected_changes, f"Unexpected file changes: {changed - expected_changes}"


# ---------------------------------------------------------------------------
# Phase 4: User Story 2 - Guardrails (T022-T026, T025a)
# ---------------------------------------------------------------------------


def test_add_tool_fails_when_entry_point_missing(project_root: Path) -> None:
    """T022: FR-009 - Fails with hint when MCP entry point doesn't exist."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "No MCP entry point found" in output
    assert "scaffold gep --type mcp" in output


@pytest.mark.parametrize(
    "name,reason",
    [
        ("create_file", "duplicate_after_second_run"),
        ("bind_tools", "reserved_name"),
    ],
)
def test_add_tool_fails_on_duplicate_name(mcp_project: Path, name: str, reason: str) -> None:
    """T022: FR-010 - Rejects duplicate tool names."""
    if reason == "duplicate_after_second_run":
        # First run succeeds
        result1 = runner.invoke(
            app,
            ["gep", "--type", "mcp", "--add-tool", "--name", name],
            catch_exceptions=False,
        )
        assert result1.exit_code == 0

        # Second run with same name fails
        tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
        original_content = tools_py.read_text()

        result2 = runner.invoke(
            app,
            ["gep", "--type", "mcp", "--add-tool", "--name", name],
            catch_exceptions=False,
        )
        assert result2.exit_code == 1
        output = strip_ansi(result2.stdout)
        assert f"tool named '{name}' already exists" in output

        # File unchanged after failed run
        assert tools_py.read_text() == original_content

    elif reason == "reserved_name":
        tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
        original_content = tools_py.read_text()

        result = runner.invoke(
            app,
            ["gep", "--type", "mcp", "--add-tool", "--name", name],
            catch_exceptions=False,
        )
        assert result.exit_code == 1
        output = strip_ansi(result.stdout)
        assert "'bind_tools' is reserved" in output

        # File unchanged after failed run
        assert tools_py.read_text() == original_content


def test_add_tool_fails_on_decorator_vs_function_name_duplicate(mcp_project: Path) -> None:
    """T022: FR-010 - Rejects both @mcp.tool name and function name as duplicates."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"

    # Add a tool using the actual command where decorator name != function name
    # First add normally
    result_add = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "search"],
        catch_exceptions=False,
    )
    assert result_add.exit_code == 0

    # Hand-edit to rename the function but keep the decorator name
    original = tools_py.read_text()
    modified = original.replace("async def search(", "async def do_search(")
    tools_py.write_text(modified)

    # Try to add tool with decorator name "search" - should fail
    result1 = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "search"],
        catch_exceptions=False,
    )
    assert result1.exit_code == 1
    assert "tool named 'search' already exists" in strip_ansi(result1.stdout)

    # Try to add tool with function name "do_search" - should also fail
    result2 = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "do_search"],
        catch_exceptions=False,
    )
    assert result2.exit_code == 1
    assert "tool named 'do_search' already exists" in strip_ansi(result2.stdout)


@pytest.mark.parametrize(
    "flag_name,flag_value",
    [
        ("--swagger", "spec.yaml"),
        ("--enable-kafka", None),
        ("--enable-mcp-client", None),
        ("--with-resources", None),
        ("--with-prompts", None),
    ],
)
def test_add_tool_incompatible_with_creation_flags(mcp_project: Path, flag_name: str, flag_value: str | None) -> None:
    """T023: FR-011 - --add-tool is incompatible with creation-only flags."""
    args = ["gep", "--type", "mcp", "--add-tool", "--name", "create_file", flag_name]
    if flag_value is not None:
        args.append(flag_value)

    result = runner.invoke(app, args, catch_exceptions=False)
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "--add-tool is incompatible with" in output
    assert flag_name.lstrip("-") in output


@pytest.mark.parametrize(
    "type_value",
    [
        "restapi",
        "agent",
        "generic",
        None,  # --type omitted
    ],
)
def test_add_tool_requires_type_mcp(project_root: Path, type_value: str | None) -> None:
    """T023: FR-012 - --add-tool requires --type mcp."""
    args = ["gep", "--add-tool", "--name", "create_file"]
    if type_value is not None:
        args.extend(["--type", type_value])

    result = runner.invoke(app, args, catch_exceptions=False)
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "--add-tool" in output and "mcp" in output


def test_add_tool_requires_name_flag(mcp_project: Path) -> None:
    """T024: FR-002 - --name is required with --add-tool."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "--name is required" in output


@pytest.mark.parametrize(
    "name,expected_message_fragment",
    [
        ("CreateFile", "snake_case"),
        ("class", "keyword"),
    ],
)
def test_add_tool_validates_name_format(mcp_project: Path, name: str, expected_message_fragment: str) -> None:
    """T024: FR-003 - Validates --name format and rejects keywords."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", name],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert expected_message_fragment in output


def test_add_tool_accepts_soft_keywords(mcp_project: Path) -> None:
    """T024: FR-003 - Soft keywords like 'match' are accepted."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "match"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "param,expected_fragment",
    [
        ("path", "Expected 'name:type' format"),
        ("Path:str", "snake_case"),
        ("path:print('x')", "type-expression"),
        ("class:str", "keyword"),
    ],
)
def test_add_tool_validates_param_format(mcp_project: Path, param: str, expected_fragment: str) -> None:
    """T024: FR-005 - Validates --param format."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file", "--param", param],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout).replace("\n", " ")
    assert expected_fragment in output


def test_add_tool_rejects_duplicate_param_names(mcp_project: Path) -> None:
    """T024: FR-006 - Rejects duplicate --param names."""
    result = runner.invoke(
        app,
        [
            "gep",
            "--type",
            "mcp",
            "--add-tool",
            "--name",
            "create_file",
            "--param",
            "path:str",
            "--param",
            "path:int",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "Duplicate" in output and "path" in output


def test_add_tool_validates_returns_type(mcp_project: Path) -> None:
    """T024: FR-007 - Validates --returns type expression."""
    result = runner.invoke(
        app,
        [
            "gep",
            "--type",
            "mcp",
            "--add-tool",
            "--name",
            "create_file",
            "--returns",
            "print('x')",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "not a recognizable type-expression" in output or "Invalid --returns" in output


def test_add_tool_rejects_unsafe_description(mcp_project: Path) -> None:
    """T025: FR-008 - Rejects --description with embedded triple quotes."""
    result = runner.invoke(
        app,
        [
            "gep",
            "--type",
            "mcp",
            "--add-tool",
            "--name",
            "create_file",
            "--description",
            'A docstring with """ embedded',
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "triple-quote" in output


def test_add_tool_fails_on_legacy_project_missing_bind_tools(mcp_project: Path) -> None:
    """T025: FR-017 - Fails gracefully when bind_tools is missing."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    original_content = tools_py.read_text()

    # Remove bind_tools function
    modified = original_content.replace("async def bind_tools", "async def old_bind_tools")
    tools_py.write_text(modified)

    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "older scaffold version" in output or "does not support --add-tool" in output
    assert "scaffold gep --type mcp" in output

    # File unchanged
    assert tools_py.read_text() == modified


def test_add_tool_fails_when_bind_tools_not_last(mcp_project: Path) -> None:
    """T025: FR-017 - Fails when bind_tools is not the last function."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    original_content = tools_py.read_text()

    # Add a helper function after bind_tools
    modified = original_content + "\n\ndef helper() -> None:\n    pass\n"
    tools_py.write_text(modified)

    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "does not support --add-tool" in output
    assert "scaffold gep --type mcp" in output

    # File unchanged
    assert tools_py.read_text() == modified


def test_add_tool_fails_when_tools_py_missing(mcp_project: Path) -> None:
    """T025: FR-017 - Fails gracefully when tools.py is missing."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    tools_py.unlink()

    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "No MCP entry point found" in output


def test_add_tool_fails_when_test_tools_py_missing(mcp_project: Path) -> None:
    """T025: FR-017 rule 10b - Fails when test_tools.py is missing."""
    test_tools_py = mcp_project / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    original_tools = tools_py.read_text()

    test_tools_py.unlink()

    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "test_tools.py" in output
    # Message spans multiple lines, check both parts
    assert "missing" in output and "does not have" in output

    # tools.py unchanged
    assert tools_py.read_text() == original_tools


def test_add_tool_fails_when_test_structure_invalid(mcp_project: Path) -> None:
    """T025: FR-017 rule 10b - Fails when test structure is unrecognized."""
    test_tools_py = mcp_project / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    original_tools = tools_py.read_text()

    # Remove _make_mock_mcp helper
    modified_test = test_tools_py.read_text().replace("def _make_mock_mcp", "def _removed_make_mock_mcp")
    test_tools_py.write_text(modified_test)

    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "test_tools.py" in output
    assert "does not have" in output

    # tools.py unchanged
    assert tools_py.read_text() == original_tools


@pytest.mark.skipif(
    __import__("sys").platform == "win32" or __import__("os").geteuid() == 0,
    reason="Permission checks not enforced on Windows or when running as root",
)
def test_add_tool_fails_when_test_file_not_writable(mcp_project: Path) -> None:
    """T025a: FR-019 - Fails before any write when test file is read-only."""
    import stat

    test_tools_py = mcp_project / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    original_tools = tools_py.read_text()

    # Make test_tools.py read-only
    test_tools_py.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    try:
        result = runner.invoke(
            app,
            ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
            catch_exceptions=False,
        )
        assert result.exit_code == 1
        output = strip_ansi(result.stdout)
        assert "Cannot write to" in output
        assert "test_tools.py" in output

        # tools.py unchanged
        assert tools_py.read_text() == original_tools
    finally:
        # Restore permissions
        test_tools_py.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


def test_add_tool_restores_on_write_failure(mcp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T025a: FR-019 rule 13 - Restores files when write fails partway through."""
    from scaffold_ca_python.core.file_writer import FileWriter

    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    test_tools_py = mcp_project / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"
    original_tools = tools_py.read_text()
    original_tests = test_tools_py.read_text()

    # Monkeypatch _apply_append_to_file to fail on second call
    from scaffold_ca_python.models.file_operation import AppendToFile

    original_apply = FileWriter._apply_append_to_file
    call_count = [0]

    def failing_apply(op: AppendToFile) -> None:
        call_count[0] += 1
        if call_count[0] == 2:
            raise OSError("Simulated write failure")
        return original_apply(op)

    monkeypatch.setattr(FileWriter, "_apply_append_to_file", staticmethod(failing_apply))

    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "Failed to write" in output
    assert "restored" in output

    # Both files unchanged
    assert tools_py.read_text() == original_tools
    assert test_tools_py.read_text() == original_tests


def test_add_tool_guard_ordering_format_before_project(project_root: Path) -> None:
    """T026: Guard ordering - format validation (FR-005) before project check (FR-009)."""
    # No MCP entry point exists (would trigger FR-009)
    # But invalid param should fail first (FR-005)
    result = runner.invoke(
        app,
        [
            "gep",
            "--type",
            "mcp",
            "--add-tool",
            "--name",
            "create_file",
            "--param",
            "path:print('x')",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout).replace("\n", " ")
    # Should see FR-005 message about invalid type, NOT FR-009 about missing entry point
    assert "type-expression" in output
    assert "No MCP entry point found" not in output


def test_add_tool_guard_ordering_structure_before_duplicate(mcp_project: Path) -> None:
    """T026: Guard ordering - bind_tools check (FR-017) before duplicate check (FR-010)."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"

    # First add a tool so duplicate would apply
    result1 = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result1.exit_code == 0

    # Now remove bind_tools (would trigger FR-017) AND try duplicate name (would trigger FR-010)
    modified = tools_py.read_text().replace("async def bind_tools", "async def old_bind_tools")
    tools_py.write_text(modified)

    result2 = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result2.exit_code == 1
    output = strip_ansi(result2.stdout)
    # Should see FR-017 message about legacy/missing bind_tools, NOT FR-010 about duplicate
    assert "does not support --add-tool" in output
    assert "tool named 'create_file' already exists" not in output


# ---------------------------------------------------------------------------
# Phase 5: User Story 3 - --dry-run Preview (T031-T032)
# ---------------------------------------------------------------------------


def test_add_tool_dry_run_shows_preview_without_modifying_files(mcp_project: Path) -> None:
    """T031(1): --dry-run shows preview and leaves files unchanged."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    test_tools_py = mcp_project / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"

    # Take snapshot before
    original_tools = tools_py.read_bytes()
    original_tests = test_tools_py.read_bytes()

    # Run with --dry-run
    result = runner.invoke(
        app,
        [
            "gep",
            "--type",
            "mcp",
            "--add-tool",
            "--name",
            "create_file",
            "--param",
            "path:str",
            "--returns",
            "str",
            "--dry-run",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    output = strip_ansi(result.stdout)

    # Should show preview messages
    assert "Dry run:" in output or "Would modify:" in output
    assert "tools.py" in output
    assert "test_tools.py" in output
    assert "create_file" in output

    # Files should be unchanged
    assert tools_py.read_bytes() == original_tools
    assert test_tools_py.read_bytes() == original_tests


def test_add_tool_dry_run_preview_matches_actual_run(mcp_project: Path) -> None:
    """T031(2): --dry-run preview matches actual run output."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    test_tools_py = mcp_project / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"

    # Run with --dry-run
    dry_result = runner.invoke(
        app,
        [
            "gep",
            "--type",
            "mcp",
            "--add-tool",
            "--name",
            "create_file",
            "--param",
            "path:str",
            "--returns",
            "str",
            "--dry-run",
        ],
        catch_exceptions=False,
    )
    assert dry_result.exit_code == 0

    # Extract preview content (look for code between preview markers)
    dry_output = dry_result.stdout

    # Run without --dry-run
    actual_result = runner.invoke(
        app,
        [
            "gep",
            "--type",
            "mcp",
            "--add-tool",
            "--name",
            "create_file",
            "--param",
            "path:str",
            "--returns",
            "str",
        ],
        catch_exceptions=False,
    )
    assert actual_result.exit_code == 0

    # Read actual file contents
    actual_tools = tools_py.read_text()
    actual_tests = test_tools_py.read_text()

    # Preview should contain the tool function signature
    assert "async def create_file" in dry_output
    assert "path: str" in dry_output
    assert "-> str" in dry_output

    # Actual files should contain the same
    assert "async def create_file" in actual_tools
    assert "path: str" in actual_tools
    assert "-> str" in actual_tools
    assert "test_bind_tools_registers_create_file" in actual_tests


def test_add_tool_dry_run_fails_on_missing_entry_point(project_root: Path) -> None:
    """T031(3): --dry-run with missing entry point fails before showing preview."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file", "--dry-run"],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    output = strip_ansi(result.stdout)

    # Should see FR-009 error, NOT preview output
    assert "No MCP entry point found" in output
    assert "Dry run:" not in output
    assert "Would modify:" not in output
