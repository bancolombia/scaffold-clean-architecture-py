"""Tests for UseCaseFactory."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext) -> ModuleContext:
    return ModuleContext(name="create-order", project=project)


def test_use_case_files_queued_in_dry_run(tmp_path: Path) -> None:
    """Verify UseCaseFactory.build() queues expected files."""
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=True)

    from scaffold_ca_python.factory.simple.use_case_factory import UseCaseFactory

    factory = UseCaseFactory()
    factory.build(builder)

    preview = builder.persist()

    # Verify all use case files are queued:
    # - src: create_order_usecase.py
    # - tests: test_create_order_usecase.py

    src_dir = tmp_path / "src" / "ms_demo" / "domain" / "usecase"
    test_dir = tmp_path / "src" / "tests" / "domain" / "usecase"

    expected_files = [
        src_dir / "create_order_usecase.py",
        test_dir / "test_create_order_usecase.py",
    ]

    for expected in expected_files:
        assert expected in preview, f"Expected {expected.relative_to(tmp_path)} in preview"


def test_use_case_no_dependencies_injected(tmp_path: Path) -> None:
    """Verify UseCaseFactory does not add dependencies."""
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=False)

    from scaffold_ca_python.factory.simple.use_case_factory import UseCaseFactory

    factory = UseCaseFactory()
    factory.build(builder)

    _ = builder.persist()
    pyproject = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")

    # Verify no dependencies added
    assert "boto3" not in pyproject, "Unexpected boto3 in pyproject.toml"
    assert "httpx" not in pyproject, "Unexpected httpx in pyproject.toml"
