"""Tests for DeleteModuleFactory."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext, name: str = "order-handler") -> ModuleContext:
    return ModuleContext(name=name, project=project)


def _create_test_helper(root: Path, snake_name: str) -> None:
    """Create a test helper module to delete."""
    src_dir = root / "src" / "ms_demo" / "infrastructure" / "helpers" / snake_name
    test_dir = root / "src" / "tests" / "infrastructure" / "helpers" / snake_name

    src_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "__init__.py").write_text("# helper\n", encoding="utf-8")
    (src_dir / f"{snake_name}.py").write_text("# helper impl\n", encoding="utf-8")
    (test_dir / f"test_{snake_name}.py").write_text("# helper test\n", encoding="utf-8")


def test_delete_module_removes_helper(tmp_path: Path) -> None:
    """Verify DeleteModuleFactory.build() removes helper module."""
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()

    # Create a helper to delete
    _create_test_helper(tmp_path, "order_handler")

    # Verify exists before
    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "helpers" / "order_handler"
    assert src_dir.exists(), "Test setup: helper should exist"

    # Build deletion via factory
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project, "order-handler"),
        dry_run=False,
    )

    from scaffold_ca_python.factory.simple.delete_module_factory import DeleteModuleFactory

    factory = DeleteModuleFactory()
    factory.build(builder)

    # Persist (DeleteModuleFactory handles deletion directly, not through builder)
    _ = builder.persist()

    # Verify helper was deleted
    assert not src_dir.exists(), "Helper directory should be deleted"
