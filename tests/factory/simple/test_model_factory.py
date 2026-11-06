"""Tests for ModelFactory."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext) -> ModuleContext:
    return ModuleContext(name="order", project=project)


def test_model_files_queued_in_dry_run(tmp_path: Path) -> None:
    """: Verify ModelFactory.build() queues expected files."""
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=True)

    from scaffold_ca_python.factory.simple.model_factory import ModelFactory

    factory = ModelFactory()
    factory.build(builder)

    preview = builder.persist()

    # Verify all model files are queued:
    # - src: order.py
    # - tests: test_order.py

    src_dir = tmp_path / "src" / "ms_demo" / "domain" / "model"
    test_dir = tmp_path / "src" / "tests" / "domain" / "model"

    expected_files = [
        src_dir / "order" / "__init__.py",
        src_dir / "order" / "order.py",
        src_dir / "order" / "gateways" / "__init__.py",
        src_dir / "order" / "gateways" / "order_repository.py",
        test_dir / "order" / "test_order.py",
        test_dir / "order" / "gateways" / "test_order_repository.py",
    ]
    assert len(preview) == 6

    for expected in expected_files:
        assert expected in preview, f"Expected {expected.relative_to(tmp_path)} in preview"


def test_model_no_dependencies_injected(tmp_path: Path) -> None:
    """: Verify ModelFactory does not add dependencies."""
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=False)

    from scaffold_ca_python.factory.simple.model_factory import ModelFactory

    factory = ModelFactory()
    factory.build(builder)

    _ = builder.persist()
    pyproject = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")

    # Verify no dependencies added (models use only pydantic which is already a dep)
    # Pyproject should only contain the original content
    assert "boto3" not in pyproject, "Unexpected boto3 in pyproject.toml"
    assert "httpx" not in pyproject, "Unexpected httpx in pyproject.toml"
