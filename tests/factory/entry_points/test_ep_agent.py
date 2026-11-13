"""Tests for EntryPointAgent factory (A2A server)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.factory.dependencies import A2A_RUNTIME
from scaffold_ca_python.factory.entry_points.ep_agent import EntryPointAgent
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject

_PKG = Path("src", "ms_demo")
_SRC = _PKG / "infrastructure" / "entry_points" / "a2a_server"
_TESTS = Path("src", "tests", "infrastructure", "entry_points", "a2a_server")


def _make_builder(tmp_path: Path, *, dry_run: bool = True) -> ModuleBuilder:
    write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    return ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=ModuleContext(name="agent", project=project),
        dry_run=dry_run,
    )


def _write_project_files(tmp_path: Path) -> Path:
    """Simulate the config.py and main.py that `scaffold ca` creates."""
    config_py = tmp_path / _PKG / "application" / "config" / "config.py"
    config_py.parent.mkdir(parents=True, exist_ok=True)
    config_py.write_text('class Settings:\n    LOG_LEVEL: str = "INFO"\n', encoding="utf-8")
    main_py = tmp_path / _PKG / "main.py"
    main_py.write_text("def main() -> None: ...\n", encoding="utf-8")
    return config_py


@pytest.mark.parametrize(
    "rel_path",
    [
        _SRC / "__init__.py",
        _SRC / "agent_settings.py",
        _SRC / "a2a_config.py",
        _SRC / "agent_executor.py",
        _SRC / "agent_card.py",
        _SRC / "routes.py",
        _TESTS / "test_agent_executor.py",
        _TESTS / "test_agent_card.py",
        _TESTS / "test_routes.py",
        _PKG / "server.py",
        _PKG / "application" / "app.py",
        Path("src", "tests", "application", "test_app.py"),
    ],
)
def test_agent_files_queued_in_dry_run(tmp_path: Path, rel_path: Path) -> None:
    builder = _make_builder(tmp_path)
    EntryPointAgent().build(builder)
    assert tmp_path / rel_path in builder.persist()


def test_agent_sets_server_main_script(tmp_path: Path) -> None:
    builder = _make_builder(tmp_path)
    EntryPointAgent().build(builder)
    assert builder.pending_project_script == "main"


def test_agent_live_run_replaces_main_and_configures_server(tmp_path: Path) -> None:
    config_py = _write_project_files(tmp_path)
    builder = _make_builder(tmp_path, dry_run=False)

    EntryPointAgent().build(builder)
    builder.persist()

    assert not (tmp_path / _PKG / "main.py").exists()
    assert "def main() -> None:" in (tmp_path / _PKG / "server.py").read_text(encoding="utf-8")
    config = config_py.read_text(encoding="utf-8")
    assert 'HOST: str = "0.0.0.0"' in config
    assert "PORT: int = 8000" in config
    pyproject = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    for dep in A2A_RUNTIME:
        assert dep in pyproject, f"Missing dep: {dep}"
    assert 'ms-demo = "ms_demo.server:main"' in pyproject


def test_agent_app_py_not_overwritten(tmp_path: Path) -> None:
    _write_project_files(tmp_path)
    app_py = tmp_path / _PKG / "application" / "app.py"
    app_py.write_text("# SENTINEL\n", encoding="utf-8")
    builder = _make_builder(tmp_path, dry_run=False)

    EntryPointAgent().build(builder)

    with pytest.raises(FileExistsError):
        builder.persist()
    assert app_py.read_text(encoding="utf-8") == "# SENTINEL\n"


def test_agent_dry_run_notes_announce_server_main(tmp_path: Path) -> None:
    _write_project_files(tmp_path)
    notes = EntryPointAgent().result_notes(tmp_path / _PKG, "ms_demo", "agent", dry_run=True)
    assert any("Would delete: src/ms_demo/main.py" in n for n in notes)
    assert any('"ms_demo.server:main"' in n for n in notes)
