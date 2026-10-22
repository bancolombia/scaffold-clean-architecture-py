"""Extensibility contract: adding a new type without touching commands/ (T011).

A new module type must be addable by registering an EntryPointFactory subclass
under a fresh key in ENTRY_POINT_FACTORIES, with no edits to any command file.
This test registers a fake factory and verifies the command dispatches to it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from scaffold_ca_python.core.module_builder import ModuleBuilder
from tests.conftest import strip_ansi

runner = CliRunner()


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Scaffold a real CA project and chdir into it."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    return project_dir


@pytest.fixture()
def restapi_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """CA project with a restapi entry point already created."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    runner.invoke(app, ["gep", "--type", "restapi"], catch_exceptions=False)
    return project_dir


class _StubFactory:
    """Minimal EntryPointFactory-like fake used before base.py exists."""

    subdir = "stub_ep"
    supported_flags: frozenset[object] = frozenset()
    conflicts: tuple[object, ...] = ()

    def build(self, builder: ModuleBuilder) -> None:
        pass

    def result_notes(self, project_root: Path, pkg: str, type_key: str, *, dry_run: bool) -> list[str]:
        verb = "will be replaced" if dry_run else "replaced"
        return [f"[yellow]⚠[/yellow] main.py {verb} with {type_key} entrypoint."]


# ---------------------------------------------------------------------------
# After US2 is implemented, these tests use the real EntryPointFactory ABC
# and ENTRY_POINT_FACTORIES registry.
# ---------------------------------------------------------------------------


def test_stub_dry_run_invokes_build_and_shows_subdir(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(a) gep --type stub --dry-run dispatches to build(); tree title is 'stub_ep (dry run)'."""
    from scaffold_ca_python.commands import generate_entry_point  # noqa: PLC0415

    monkeypatch.setitem(generate_entry_point._REGISTRY, "stub", _StubFactory)  # type: ignore[arg-type]
    result = runner.invoke(app, ["gep", "--type", "stub", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "stub_ep" in strip_ansi(result.output)


def test_stub_does_not_require_commands_edit(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(e) After US2: commands/*.py (except add_mcp_tool.py) has no type literals."""

    commands_dir = Path(__file__).parent.parent.parent / "src" / "scaffold_ca_python" / "commands"
    literals = {"restapi", "agent", "generic", "rest-consumer", "secrets", "github", "azure"}
    violations: list[str] = []
    for py_file in commands_dir.glob("*.py"):
        if py_file.name in {"add_mcp_tool.py", "_entry_point_rules.py"}:
            continue
        content = py_file.read_text(encoding="utf-8")
        for lit in literals:
            if f'"{lit}"' in content or f"'{lit}'" in content:
                violations.append(f"{py_file.name}: '{lit}'")
    # This assertion will fail until US2 is implemented; that's intentional.
    assert violations == [], f"Type literals found in commands/: {violations}"
