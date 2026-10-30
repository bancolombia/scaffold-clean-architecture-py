"""T028: add-mcp-tool wireup pattern tests.

Verify that --add-tool stubs use Injected[...] patterns (wireup) and
contain no legacy dependency-injector patterns (@inject, Provide[]).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app

runner = CliRunner()


@pytest.fixture
def mcp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a project with an MCP entry point."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    runner.invoke(app, ["gep", "--type", "mcp"], catch_exceptions=False)
    return project_dir


def test_mcp_tools_has_injected_import(mcp_project: Path) -> None:
    """T028: Initial tools.py must import Injected from wireup."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "Injected" in content
    assert "wireup" in content


def test_mcp_tools_has_no_inject_decorator(mcp_project: Path) -> None:
    """T028: tools.py must not use legacy @inject decorator."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "@inject" not in content


def test_mcp_tools_has_no_provide_pattern(mcp_project: Path) -> None:
    """T028: tools.py must not use legacy Provide[...] pattern."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "Provide[" not in content


def test_add_tool_stub_has_no_inject_decorator(mcp_project: Path) -> None:
    """T028: appended tool stub must not use legacy @inject decorator."""
    runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "@inject" not in content


def test_add_tool_stub_has_no_provide_pattern(mcp_project: Path) -> None:
    """T028: appended tool stub must not use legacy Provide[...] pattern."""
    runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "Provide[" not in content


def test_add_tool_preserves_injected_import(mcp_project: Path) -> None:
    """T028: after --add-tool, Injected import must still be present in tools.py."""
    runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "fetch_data", "--param", "query:str"],
        catch_exceptions=False,
    )
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "Injected" in content
    assert "wireup" in content
