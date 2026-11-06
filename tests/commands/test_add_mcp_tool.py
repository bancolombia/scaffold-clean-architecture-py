""": add-mcp-tool wireup pattern tests.

Verify that --add-tool stubs use Injected[...] patterns (wireup) and
contain no legacy dependency-injector patterns (@inject, Provide[]).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app

runner = CliRunner()


def test_mcp_tools_has_injected_import(mcp_project: Path) -> None:
    """: Initial tools.py must import Injected from wireup."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "Injected" in content
    assert "wireup" in content


def test_mcp_tools_has_no_inject_decorator(mcp_project: Path) -> None:
    """: tools.py must not use legacy @inject decorator."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "@inject" not in content


def test_mcp_tools_has_no_provide_pattern(mcp_project: Path) -> None:
    """: tools.py must not use legacy Provide[...] pattern."""
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "Provide[" not in content


def test_add_tool_stub_has_no_inject_decorator(mcp_project: Path) -> None:
    """: appended tool stub must not use legacy @inject decorator."""
    runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "@inject" not in content


def test_add_tool_stub_has_no_provide_pattern(mcp_project: Path) -> None:
    """: appended tool stub must not use legacy Provide[...] pattern."""
    runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "create_file"],
        catch_exceptions=False,
    )
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "Provide[" not in content


def test_persist_restore_failure_reports_inconsistent_state(mcp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_write_text = Path.write_text
    calls = {"n": 0}

    def flaky_write_text(self: Path, data: str, *args: object, **kwargs: object) -> int:
        calls["n"] += 1
        if calls["n"] >= 2:
            raise OSError("disk full")
        return real_write_text(self, data, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", flaky_write_text)
    result = runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "broken_tool"],
    )
    assert result.exit_code == 1
    assert "also failed" in result.output
    assert "was restored" not in result.output


def test_add_tool_preserves_injected_import(mcp_project: Path) -> None:
    """: after --add-tool, Injected import must still be present in tools.py."""
    runner.invoke(
        app,
        ["gep", "--type", "mcp", "--add-tool", "--name", "fetch_data", "--param", "query:str"],
        catch_exceptions=False,
    )
    tools_py = mcp_project / "src" / "my_app" / "infrastructure" / "entry_points" / "mcp_server" / "tools.py"
    content = tools_py.read_text()
    assert "Injected" in content
    assert "wireup" in content
