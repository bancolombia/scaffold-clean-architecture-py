"""Tests for EntryPointMcp factory ( /  019-restructure)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext, subtype: str = "mcp") -> ModuleContext:
    return ModuleContext(name="mcp_server", project=project)


def _make_builder(tmp_path: Path, *, dry_run: bool = True) -> ModuleBuilder:
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    return ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=dry_run,
    )


def test_mcp_files_queued_in_dry_run(tmp_path: Path) -> None:
    """tools.py present; no server.py inside mcp_server/."""
    builder = _make_builder(tmp_path)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "entry_points" / "mcp_server"
    test_dir = tmp_path / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server"

    assert src_dir / "__init__.py" in preview
    assert src_dir / "tools.py" in preview
    assert test_dir / "test_tools.py" in preview

    # Old monolithic server.py must NOT be generated inside mcp_server/
    assert src_dir / "server.py" not in preview


def test_mcp_with_resources_queues_resources_file(tmp_path: Path) -> None:
    """--with-resources adds resources.py and test_resources.py."""
    builder = _make_builder(tmp_path)
    builder.add_param("with_resources", True)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "entry_points" / "mcp_server"
    test_dir = tmp_path / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server"

    assert src_dir / "resources.py" in preview
    assert test_dir / "test_resources.py" in preview


def test_mcp_without_resources_does_not_queue_resources_file(tmp_path: Path) -> None:
    """without --with-resources no resources.py is generated."""
    builder = _make_builder(tmp_path)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "entry_points" / "mcp_server"
    assert src_dir / "resources.py" not in preview


def test_mcp_with_prompts_queues_prompts_file(tmp_path: Path) -> None:
    """--with-prompts adds prompts.py and test_prompts.py."""
    builder = _make_builder(tmp_path)
    builder.add_param("with_prompts", True)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "entry_points" / "mcp_server"
    test_dir = tmp_path / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server"

    assert src_dir / "prompts.py" in preview
    assert test_dir / "test_prompts.py" in preview


def test_mcp_without_prompts_does_not_queue_prompts_file(tmp_path: Path) -> None:
    """without --with-prompts no prompts.py is generated."""
    builder = _make_builder(tmp_path)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "entry_points" / "mcp_server"
    assert src_dir / "prompts.py" not in preview


def test_mcp_dependencies_injected(tmp_path: Path) -> None:
    """(H3): all five required deps are present after a live run."""
    builder = _make_builder(tmp_path, dry_run=False)

    # Simulate the config.py that `scaffold ca` would have created first.
    config_py = tmp_path / "src" / "ms_demo" / "application" / "config" / "config.py"
    config_py.parent.mkdir(parents=True, exist_ok=True)
    config_py.write_text(
        '"""Application settings."""\nclass Settings:\n    LOG_LEVEL: str = "INFO"\n',
        encoding="utf-8",
    )

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    builder.persist()

    pyproject = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    expected_deps = [
        "mcp~=1.30.0",
        "uvicorn[standard]~=0.53.0",
        "starlette~=1.6.0",
        "wireup~=2.13.0",
        "pydantic-settings~=2.15.0",
    ]
    for dep in expected_deps:
        assert dep in pyproject, f"Missing dep: {dep}"


def test_mcp_scripts_entry_fn_param_is_main(tmp_path: Path) -> None:
    """Factory must set pending_project_script='main' on builder."""
    builder = _make_builder(tmp_path)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)

    assert builder.pending_project_script == "main"


def test_mcp_main_py_overwritten(tmp_path: Path) -> None:
    """server.py at package root replaces main.py.

    This test is intentionally placed here to fail until +
    add server.py generation to ep_mcp.py.  It documents the expected
     behaviour so the red/green boundary is explicit.
    """
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=True,
    )

    main_py = tmp_path / "src" / "ms_demo" / "main.py"
    main_py.parent.mkdir(parents=True, exist_ok=True)
    main_py.write_text("# placeholder\n", encoding="utf-8")

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    # server.py at package root must be queued (implemented in  / )
    server_py = tmp_path / "src" / "ms_demo" / "server.py"
    assert server_py in preview, f"Expected {server_py.relative_to(tmp_path)} in preview"


#  /  — application/app.py composition root


def test_mcp_queues_app_py(tmp_path: Path) -> None:
    """application/app.py must be in the dry-run preview."""
    builder = _make_builder(tmp_path)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    app_py = tmp_path / "src" / "ms_demo" / "application" / "app.py"
    assert app_py in preview, f"Expected {app_py.relative_to(tmp_path)} in preview"


def test_mcp_app_py_not_overwritten(tmp_path: Path) -> None:
    """existing application/app.py raises FileExistsError (no-overwrite guard)."""
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()

    # Pre-create config.py (created by `scaffold ca` in real usage).
    config_py = tmp_path / "src" / "ms_demo" / "application" / "config" / "config.py"
    config_py.parent.mkdir(parents=True, exist_ok=True)
    config_py.write_text('class Settings:\n    LOG_LEVEL: str = "INFO"\n', encoding="utf-8")

    # Pre-create app.py with sentinel content
    app_py = tmp_path / "src" / "ms_demo" / "application" / "app.py"
    app_py.parent.mkdir(parents=True, exist_ok=True)
    app_py.write_text("# SENTINEL — do not overwrite\n", encoding="utf-8")

    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=False,
    )

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    with pytest.raises(FileExistsError):
        builder.persist()


@pytest.mark.parametrize("with_resources", [True, False])
@pytest.mark.parametrize("with_prompts", [True, False])
def test_mcp_queues_routes_py(tmp_path: Path, with_resources: bool, with_prompts: bool) -> None:
    """027: routes.py is always queued, independent of optional flags."""
    builder = _make_builder(tmp_path)
    builder.add_param("with_resources", with_resources)
    builder.add_param("with_prompts", with_prompts)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "entry_points" / "mcp_server"
    assert src_dir / "routes.py" in preview


def test_mcp_queues_test_routes_py(tmp_path: Path) -> None:
    """027: test_routes.py is queued."""
    builder = _make_builder(tmp_path)

    from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp

    EntryPointMcp().build(builder)
    preview = builder.persist()

    test_dir = tmp_path / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server"
    assert test_dir / "test_routes.py" in preview
