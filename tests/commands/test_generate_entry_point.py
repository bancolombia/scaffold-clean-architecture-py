"""Tests for gep / generate-entry-point command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.helpers import strip_ansi

runner = CliRunner()


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


# restapi type


def test_restapi_server_py_is_thin_wrapper(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0
    content = (project_root / "src" / "my_app" / "server.py").read_text()
    assert "FastAPI" not in content
    meaningful_lines = [ln for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert len(meaningful_lines) <= 5


def test_restapi_no_main_py(project_root: Path) -> None:
    # main.py is created by scaffold ca; gep --type restapi must not create it if absent
    (project_root / "src" / "my_app" / "main.py").unlink(missing_ok=True)
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert not (project_root / "src" / "my_app" / "main.py").exists()


def test_restapi_dry_run_includes_app_py_not_main(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "app.py" in result.output
    # main.py must not appear as a *created* file — it appears as a deletion notice
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


# test files emitted by gep --type restapi


# Existing file-existence tests


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


# restapi + --swagger


def test_swagger_injects_routes(project_root: Path, swagger_file: Path) -> None:
    result = runner.invoke(
        app,
        ["gep", "--type", "restapi", "--swagger", str(swagger_file)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    controller = (
        project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api" / "v1" / "rest_controller.py"
    )
    content = controller.read_text()
    assert '"/users"' in content
    assert '"/health"' in content


# agent type


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


# mcp type


def test_mcp_no_monolithic_server_py_in_mcp_server(project_root: Path) -> None:
    """old monolithic server.py must NOT exist inside mcp_server/ after restructure."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    server_py = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "server.py"
    assert not server_py.exists()


def test_mcp_without_resources_no_resources_py(project_root: Path) -> None:
    """without --with-resources no resources.py is created."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    resources_py = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "resources.py"
    assert not resources_py.exists()


def test_mcp_without_prompts_no_prompts_py(project_root: Path) -> None:
    """without --with-prompts no prompts.py is created."""
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    prompts_py = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "prompts.py"
    assert not prompts_py.exists()


def test_mcp_flags_rejected_for_restapi_type(project_root: Path) -> None:
    """--with-resources with non-mcp type exits 1 with hint."""
    result = runner.invoke(app, ["gep", "--type", "restapi", "--with-resources"])
    assert result.exit_code == 1
    assert "only valid with --type mcp" in result.output


def test_mcp_prompts_flag_rejected_for_agent_type(project_root: Path) -> None:
    """--with-prompts with non-mcp type exits 1 with hint."""
    result = runner.invoke(app, ["gep", "--type", "agent", "--with-prompts"])
    assert result.exit_code == 1
    assert "only valid with --type mcp" in result.output


# generic type


# Alias


def test_generate_entry_point_alias_works(project_root: Path) -> None:
    result = runner.invoke(app, ["generate-entry-point", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0


# Dry-run


def test_dry_run_writes_nothing(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (
        project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api" / "v1" / "rest_controller.py"
    ).exists()


def test_dry_run_prints_paths(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert "api" in result.output or "v1" in result.output or "server.py" in result.output


# Error cases


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


# : main.py overwritten (agent / mcp / generic only)


def test_agent_overwrites_main_py(project_root: Path) -> None:
    main_py = project_root / "src" / "my_app" / "main.py"
    runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    content = main_py.read_text()
    assert "def main" in content
    assert "asyncio" in content


def test_mcp_replaces_main_py_with_server(project_root: Path) -> None:
    """gep --type mcp writes server.py at the package root.

    When  is implemented, ep_mcp.py will:
      - add server.py.jinja2 at <pkg>/server.py (uvicorn entrypoint)
      - set scripts_entry=True so pyproject.toml [project.scripts] is updated

    Until then this test must remain xfail (strict) so it is visible as a
     obligation.
    """
    server_py = project_root / "src" / "my_app" / "server.py"
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    assert server_py.exists(), "server.py must exist after gep --type mcp"
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


# : Auto-inject dependencies


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


#  Idempotency integration test


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


# gep --help epilog


def test_gep_help_shows_type_descriptions() -> None:
    result = runner.invoke(app, ["gep", "--help"])
    assert result.exit_code == 0
    assert "Types: restapi | agent | mcp | generic" in result.output


def test_gep_help_contains_examples_section() -> None:
    result = runner.invoke(app, ["gep", "--help"])
    assert result.exit_code == 0
    assert "Examples" in result.output


# no-args → help


# compatibility guard


def test_gep_restapi_blocked_when_mcp_server_exists(
    project_root: Path,
) -> None:
    """exit 1 when mcp_server/ dir already exists; no api/v1/ created."""
    conflict = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server"
    conflict.mkdir(parents=True)

    result = runner.invoke(app, ["gep", "--type", "restapi"])

    assert result.exit_code == 1
    assert not (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api").exists()
    assert "mcp_server" in result.output


def test_gep_restapi_blocked_when_agent_exists(
    project_root: Path,
) -> None:
    """exit 1 when agent/ dir already exists; no api/v1/ created."""
    conflict = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "agent"
    conflict.mkdir(parents=True)

    result = runner.invoke(app, ["gep", "--type", "restapi"])

    assert result.exit_code == 1
    assert not (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api").exists()
    assert "agent" in result.output


def test_gep_restapi_proceeds_when_no_incompatible_entry_point(
    project_root: Path,
) -> None:
    """clean project — guard must NOT block generation."""
    result = runner.invoke(app, ["gep", "--type", "restapi"])

    assert result.exit_code == 0


def test_gep_restapi_dry_run_still_reports_mcp_conflict(
    project_root: Path,
) -> None:
    """--dry-run does not bypass the compatibility guard."""
    conflict = project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server"
    conflict.mkdir(parents=True)

    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"])

    assert result.exit_code == 1
    assert not (project_root / "src" / "my_app" / "infrastructure" / "entry_points" / "api").exists()
    assert "mcp_server" in result.output


# gep --type restapi deletes main.py


def test_restapi_deletes_main_py(project_root: Path) -> None:
    """main.py created by scaffold ca must be removed after gep --type restapi."""
    main_py = project_root / "src" / "my_app" / "main.py"
    assert main_py.exists(), "fixture must create main.py via scaffold ca"
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert not main_py.exists()


def test_restapi_second_run_exits_with_duplicate_error(project_root: Path) -> None:
    """second gep --type restapi must fail on duplicate guard; main.py still absent."""
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    main_py = project_root / "src" / "my_app" / "main.py"
    # Second run — duplicate guard fires because src_dir already exists
    result = runner.invoke(app, ["gep", "--type", "restapi"])
    assert result.exit_code != 0
    assert not main_py.exists()


def test_restapi_gep_ok_when_main_py_already_absent(project_root: Path) -> None:
    """silent no-op delete — command must succeed even if main.py is already gone."""
    (project_root / "src" / "my_app" / "main.py").unlink(missing_ok=True)
    result = runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    assert result.exit_code == 0


def test_restapi_dry_run_reports_would_delete_main_py(project_root: Path) -> None:
    """dry-run must mention main.py in output; the file must NOT be deleted."""
    main_py = project_root / "src" / "my_app" / "main.py"
    assert main_py.exists()
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "main.py" in result.output
    assert main_py.exists()


# gep --type restapi updates [project.scripts]


def test_restapi_updates_project_scripts(project_root: Path) -> None:
    """[project.scripts] entry must read <pkg>.server:start_server after gep restapi."""
    import tomllib

    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.server:start_server"


def test_restapi_dry_run_reports_scripts_update(project_root: Path) -> None:
    """dry-run reports the scripts update; pyproject.toml must remain unchanged."""
    import tomllib

    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "server:start_server" in result.output
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.main:main"


def test_agent_does_not_change_project_scripts(project_root: Path) -> None:
    """gep --type agent must NOT modify [project.scripts]."""
    import tomllib

    runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.main:main"


def test_mcp_updates_pyproject_scripts_to_server_main(project_root: Path) -> None:
    """gep --type mcp must update [project.scripts] to <pkg>.server:main."""
    import tomllib

    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.server:main"


def test_mcp_deletes_main_py(project_root: Path) -> None:
    """gep --type mcp must delete main.py after creating server.py."""
    main_py = project_root / "src" / "my_app" / "main.py"
    assert main_py.exists(), "fixture must provide main.py"
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    assert not main_py.exists(), "main.py must be deleted after gep --type mcp"


def test_generic_does_not_change_project_scripts(project_root: Path) -> None:
    """gep --type generic must NOT modify [project.scripts]."""
    import tomllib

    runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["my-app"] == "my_app.main:main"


# Bidirectional exclusivity — restapi <-> mcp/agent


def test_gep_mcp_blocked_when_restapi_exists(project_root: Path) -> None:
    """mcp must be blocked when restapi entry point already exists."""
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "mcp"])
    assert result.exit_code == 1
    assert "restapi" in result.output


def test_gep_agent_blocked_when_restapi_exists(project_root: Path) -> None:
    """agent must be blocked when restapi entry point already exists."""
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "agent"])
    assert result.exit_code == 1
    assert "restapi" in result.output


def test_gep_generic_not_blocked_when_restapi_exists(project_root: Path) -> None:
    """generic is always allowed regardless of existing entry points."""
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    assert result.exit_code == 0


# application/app.py composition root


def test_mcp_app_py_with_resources_contains_bind_resources(project_root: Path) -> None:
    """gep --type mcp --with-resources must include bind_resources in app.py."""
    runner.invoke(app, ["gep", "--type", "mcp", "--with-resources"], catch_exceptions=False)
    app_py = project_root / "src" / "my_app" / "application" / "app.py"
    assert app_py.exists()
    assert "bind_resources" in app_py.read_text(encoding="utf-8")


# User Story 1: --add-tool happy path


def test_add_tool_full_flag_invocation(mcp_project: Path) -> None:
    """(1): Full-flag --add-tool invocation inserts correctly-shaped stub."""
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
    """(2): Zero --param flags produce stub with no extra parameters."""
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
    """(3): Omitted --returns/--description use defaults."""
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
    """(4): Pre-existing example_tool and its tests remain unchanged."""
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
    """(5): test_tools.py gains registration test that passes."""
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
    assert "create_file" in content
    assert "in registered" in content


def test_add_tool_only_modifies_tools_and_tests(mcp_project: Path) -> None:
    """(6): Only tools.py and test_tools.py are modified, no other files."""
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


def test_add_tool_fails_when_entry_point_missing(project_root: Path) -> None:
    """Fails with hint when MCP entry point doesn't exist."""
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
    """Rejects duplicate tool names."""
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
    """Rejects both @mcp.tool name and function name as duplicates."""
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
    """--add-tool is incompatible with creation-only flags."""
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
    """--add-tool requires --type mcp."""
    args = ["gep", "--add-tool", "--name", "create_file"]
    if type_value is not None:
        args.extend(["--type", type_value])

    result = runner.invoke(app, args, catch_exceptions=False)
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert "--add-tool" in output and "mcp" in output


def test_add_tool_requires_name_flag(mcp_project: Path) -> None:
    """--name is required with --add-tool."""
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
    """Validates --name format and rejects keywords."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", name],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout)
    assert expected_message_fragment in output


def test_add_tool_accepts_soft_keywords(mcp_project: Path) -> None:
    """Soft keywords like 'match' are accepted."""
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
    """Validates --param format."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file", "--param", param],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    output = strip_ansi(result.stdout).replace("\n", " ")
    assert expected_fragment in output


def test_add_tool_rejects_duplicate_param_names(mcp_project: Path) -> None:
    """Rejects duplicate --param names."""
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
    """Validates --returns type expression."""
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
    """Rejects --description with embedded triple quotes."""
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
    """Fails gracefully when bind_tools is missing."""
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
    """Fails when bind_tools is not the last function."""
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
    """Fails gracefully when tools.py is missing."""
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
    """rule 10b - Fails when test_tools.py is missing."""
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
    """rule 10b - Fails when test structure is unrecognized."""
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
    """Fails before any write when test file is read-only."""
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
    """rule 13 - Restores files when write fails partway through."""
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
    """Guard ordering - format validation () before project check."""
    # No MCP entry point exists (would trigger )
    # But invalid param should fail first
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
    # Should see  message about invalid type, NOT  about missing entry point
    assert "type-expression" in output
    assert "No MCP entry point found" not in output


def test_add_tool_guard_ordering_structure_before_duplicate(mcp_project: Path) -> None:
    """Guard ordering - bind_tools check () before duplicate check."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"

    # First add a tool so duplicate would apply
    result1 = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result1.exit_code == 0

    # Now remove bind_tools (would trigger ) AND try duplicate name (would trigger )
    modified = tools_py.read_text().replace("async def bind_tools", "async def old_bind_tools")
    tools_py.write_text(modified)

    result2 = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    assert result2.exit_code == 1
    output = strip_ansi(result2.stdout)
    # Should see  message about legacy/missing bind_tools, NOT  about duplicate
    assert "does not support --add-tool" in output
    assert "tool named 'create_file' already exists" not in output


# : User Story 3 - --dry-run Preview (-)


def test_add_tool_dry_run_shows_preview_without_modifying_files(mcp_project: Path) -> None:
    """(1): --dry-run shows preview and leaves files unchanged."""
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
    """(2): --dry-run preview matches actual run output."""
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
    """(3): --dry-run with missing entry point fails before showing preview."""
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file", "--dry-run"],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    output = strip_ansi(result.stdout)

    # Should see  error, NOT preview output
    assert "No MCP entry point found" in output
    assert "Dry run:" not in output
    assert "Would modify:" not in output


def test_agent_class_name_has_no_hyphens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """agent class name must be PascalCase even for hyphenated project names."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    agent_file = project_dir / "src" / "my_app" / "infrastructure" / "entry_points" / "agent" / "agent.py"
    content = agent_file.read_text()
    assert "my-app" not in content, "Class name must not contain hyphens"
    assert "MyApp" in content or "MyAppAgent" in content, "Class name must be PascalCase"


def test_agent_main_does_not_import_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main.py must not import a bare module-level run() that does not exist."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    runner.invoke(app, ["gep", "--type", "agent"], catch_exceptions=False)
    main_file = project_dir / "src" / "my_app" / "main.py"
    content = main_file.read_text()
    # main must NOT import a bare `run` from agent module — agent.agent has no module-level run()
    assert "entry_points.agent.agent import run" not in content


def test_generic_main_does_not_import_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """generic main.py must not import a bare run() that does not exist."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    runner.invoke(app, ["gep", "--type", "generic"], catch_exceptions=False)
    main_file = project_dir / "src" / "my_app" / "main.py"
    content = main_file.read_text()
    # main must NOT import a bare `run` from entry_point module — handler.py has no module-level run()
    assert "entry_points.generic.entry_point import run" not in content


def test_mcp_app_uses_inject_from_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mcp app.py must use inject_from_container, not container.wire."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    app_file = project_dir / "src" / "my_app" / "application" / "app.py"
    content = app_file.read_text()
    assert "inject_from_container" in content, "mcp app.py must use inject_from_container"
    assert "container.wire(" not in content
