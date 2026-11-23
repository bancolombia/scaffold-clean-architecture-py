"""Safety-net tests that pin the observable CLI behavior (//).

These tests must pass BEFORE and AFTER the refactor. The only assertions that
may change are those for allowed changes C-1, C-2 and C-3. See
contracts/cli-behavior.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.helpers import strip_ansi

runner = CliRunner()


@pytest.mark.parametrize(
    ("args", "expected_fragment"),
    [
        (
            ["gep", "--type", "x"],
            "Unknown type 'x'. Allowed: restapi, agent, mcp, generic.",
        ),
        (
            ["gep", "--type", "mcp", "--swagger", "f.yaml"],
            "--swagger is only valid with --type restapi.",
        ),
        (
            ["gep", "--type", "agent", "--with-prompts"],
            "--with-resources and --with-prompts are only valid with --type mcp.",
        ),
        (
            ["gep", "--add-tool"],
            "--add-tool is only valid with --type mcp.",
        ),
        (
            ["gep", "--type", "mcp", "--add-tool", "--name", "x", "--with-resources"],
            "--add-tool is incompatible with --with-resources.",
        ),
    ],
)
def test_gep_error_cases(
    args: list[str],
    expected_fragment: str,
    project_root: Path,
) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert expected_fragment in strip_ansi(result.output)


@pytest.mark.parametrize("flag", ["--enable-kafka", "--enable-mcp-client"])
def test_gep_removed_agent_flags_are_unknown(flag: str, project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent", flag])
    assert result.exit_code == 2
    assert "No such option" in strip_ansi(result.output)


def test_gep_restapi_after_mcp_conflicts(mcp_project: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"])
    assert result.exit_code == 1
    out = strip_ansi(result.output)
    assert "Incompatible entry point 'mcp'" in out
    assert "before adding restapi." in out


def test_gep_agent_after_restapi_conflicts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "api-proj"], catch_exceptions=False)
    monkeypatch.chdir(tmp_path / "api-proj")
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    result = runner.invoke(app, ["gep", "--type", "agent"])
    assert result.exit_code == 1
    out = strip_ansi(result.output)
    assert "Incompatible entry point 'restapi'" in out
    assert "before adding agent." in out


def test_gep_mcp_twice_shows_directory_exists(mcp_project: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "mcp"])
    assert result.exit_code == 1
    out = strip_ansi(result.output)
    assert "mcp_server/" in out
    assert "already" in out


def test_gda_generic_requires_name(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "generic"])
    assert result.exit_code == 1
    assert "--name is required when --type is generic." in strip_ansi(result.output)


def test_gda_unknown_type(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "x"])
    assert result.exit_code == 1
    out = strip_ansi(result.output)
    assert "Unknown type 'x'." in out
    for allowed in ("rest-consumer", "secrets", "generic", "sqlalchemy"):
        assert allowed in out


def test_conftest_header_written_once_with_two_adapters(project_root: Path) -> None:
    """Generating rest-consumer then sqlalchemy must produce only one header in conftest."""
    runner.invoke(app, ["gda", "--type", "rest-consumer"], catch_exceptions=False)
    runner.invoke(app, ["gda", "--type", "sqlalchemy"], catch_exceptions=False)
    conftest = (project_root / "src" / "tests" / "conftest.py").read_text()
    assert conftest.count("from __future__ import annotations") == 1


def test_dm_sqlalchemy_removes_fixture_leaves_rest_consumer(project_root: Path) -> None:
    """dm --name sqlalchemy removes sqlalchemy_env and preserves rest_consumer_env."""
    runner.invoke(app, ["gda", "--type", "rest-consumer"], catch_exceptions=False)
    runner.invoke(app, ["gda", "--type", "sqlalchemy"], catch_exceptions=False)
    result = runner.invoke(app, ["dm", "--name", "sqlalchemy", "--confirm"], catch_exceptions=False)
    assert result.exit_code == 0
    conftest = (project_root / "src" / "tests" / "conftest.py").read_text()
    assert "sqlalchemy_env" not in conftest
    assert "rest_consumer_env" in conftest


def test_driver_flag_on_rest_consumer_exits_1(project_root: Path) -> None:
    """--driver must only be used with --type sqlalchemy."""
    result = runner.invoke(app, ["gda", "--type", "rest-consumer", "--driver", "postgresql"])
    assert result.exit_code == 1
    assert "sqlalchemy" in strip_ansi(result.output).lower()


def test_driver_unknown_value_exits_nonzero(project_root: Path) -> None:
    """An unrecognized --driver value must produce a non-zero exit."""
    result = runner.invoke(app, ["gda", "--type", "sqlalchemy", "--driver", "oracle"])
    assert result.exit_code != 0


def test_gpipe_unknown_provider(project_root: Path) -> None:
    result = runner.invoke(app, ["gpipe", "--provider", "x"])
    assert result.exit_code == 1
    assert "Unknown provider 'x'. Allowed: github, azure." in strip_ansi(result.output)


def test_gm_duplicate(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    result = runner.invoke(app, ["gm", "--name", "order"])
    assert result.exit_code == 1
    out = strip_ansi(result.output)
    assert "domain/model/order/" in out
    assert "already exists" in out


def test_command_outside_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["gm", "--name", "thing"])
    assert result.exit_code == 1
    assert "No scaffold-ca-python project found. Run 'scaffold ca' first." in strip_ansi(result.output)


def test_dm_module_not_found(project_root: Path) -> None:
    result = runner.invoke(app, ["dm", "--name", "nope"])
    assert result.exit_code == 1
    assert "No module named 'nope' found in project." in strip_ansi(result.output)


def test_gep_restapi_dry_run_shows_would_update(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi", "--dry-run"])
    assert result.exit_code == 0
    assert 'Would update [project.scripts]: my_app = "my_app.server:start_server"' in strip_ansi(result.output)


def test_gep_restapi_shows_updated(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "restapi"])
    assert result.exit_code == 0
    assert 'Updated [project.scripts]: my_app = "my_app.server:start_server"' in strip_ansi(result.output)


def test_gep_mcp_success_message(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "mcp"])
    assert result.exit_code == 0
    out = strip_ansi(result.output)
    assert "Deleted src/my_app/main.py" in out
    assert 'Updated [project.scripts]: my_app = "my_app.server:main"' in out


def test_gep_agent_dry_run_keeps_dependency_extras(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent", "--dry-run"])
    out = " ".join(strip_ansi(result.output).split())
    assert "a2a-sdk[http-server]~=1.1.4" in out
    assert "uvicorn[standard]~=0.53.0" in out


def test_gep_agent_dry_run_announces_server_entrypoint(project_root: Path) -> None:
    result = runner.invoke(app, ["gep", "--type", "agent", "--dry-run"])
    assert result.exit_code == 0
    out = strip_ansi(result.output)
    assert "Would delete: src/my_app/main.py" in out
    assert 'Would update [project.scripts]: my_app = "my_app.server:main"' in out


def test_gep_mcp_writes_main_script(project_root: Path) -> None:
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    pyproject = (project_root / "pyproject.toml").read_text()
    assert ":main" in pyproject


@pytest.mark.parametrize(
    ("command", "required_option"),
    [
        (["gm"], "--name"),
        (["guc"], "--name"),
        (["gh"], "--name"),
        (["gep"], "--type"),
        (["gda"], "--type"),
        (["gpipe"], "--provider"),
        (["dm"], "--name"),
    ],
)
def test_command_no_args_shows_required_option(command: list[str], required_option: str) -> None:
    result = runner.invoke(app, command)
    assert result.exit_code == 0
    assert required_option in strip_ansi(result.output)


@pytest.mark.parametrize(
    "command",
    [
        ["gm", "--name", "MyOrder"],
        ["gm", "--name", "my-order"],
        ["guc", "--name", "MyOrder"],
        ["guc", "--name", "my-order"],
        ["gh", "--name", "MyHelper"],
        ["gh", "--name", "my-helper"],
        ["gda", "--type", "generic", "--name", "MyAdapter"],
        ["gda", "--type", "generic", "--name", "my-adapter"],
        ["dm", "--name", "MyModule"],
        ["dm", "--name", "my-module"],
    ],
)
def test_invalid_snake_name_rejected(project_root: Path, command: list[str]) -> None:
    result = runner.invoke(app, command)
    assert result.exit_code == 1
    assert "snake_case" in strip_ansi(result.output)


def test_commands_require_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    for command in (["gm", "--name", "x"], ["gda", "--type", "rest-consumer"], ["gep", "--type", "restapi"]):
        result = runner.invoke(app, command)
        assert result.exit_code == 1
        assert "No scaffold-ca-python project found" in strip_ansi(result.output)
