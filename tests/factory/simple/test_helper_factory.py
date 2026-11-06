"""Tests for HelperFactory."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext) -> ModuleContext:
    return ModuleContext(name="json-parser", project=project)


def test_helper_files_queued_in_dry_run(tmp_path: Path) -> None:
    """Verify HelperFactory.build() queues expected files."""
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=True)

    from scaffold_ca_python.factory.simple.helper_factory import HelperFactory

    factory = HelperFactory()
    factory.build(builder)

    preview = builder.persist()

    # Verify all helper files are queued:
    # - src: __init__.py, json_parser.py (snake_case from "JsonParser")
    # - tests: test_json_parser.py

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "helpers" / "json_parser"
    test_dir = tmp_path / "src" / "tests" / "infrastructure" / "helpers" / "json_parser"

    expected_files = [
        src_dir / "__init__.py",
        src_dir / "json_parser.py",
        test_dir / "test_json_parser.py",
    ]

    for expected in expected_files:
        assert expected in preview, f"Expected {expected.relative_to(tmp_path)} in preview"


def test_helper_no_dependencies_injected(tmp_path: Path) -> None:
    """Verify HelperFactory does not add dependencies."""
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=False)

    from scaffold_ca_python.factory.simple.helper_factory import HelperFactory

    factory = HelperFactory()
    factory.build(builder)

    _ = builder.persist()
    pyproject = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")

    # Verify no dependencies added
    assert "boto3" not in pyproject, "Unexpected boto3 in pyproject.toml"
    assert "httpx" not in pyproject, "Unexpected httpx in pyproject.toml"


def test_helper_template_has_injectable(tmp_path: Path) -> None:
    """helper template must have @wireup.injectable and infra-only docstring."""
    from scaffold_ca_python.core.module_builder import ModuleBuilder
    from scaffold_ca_python.models.context import ModuleContext, ProjectContext

    write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    module_ctx = ModuleContext(name="log_helper", project=project)
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=module_ctx, dry_run=False)

    from scaffold_ca_python.factory.simple.helper_factory import HelperFactory

    HelperFactory().build(builder)
    builder.persist()

    helper_file = tmp_path / "src" / "ms_demo" / "infrastructure" / "helpers" / "log_helper" / "log_helper.py"
    content = helper_file.read_text()
    assert "wireup" in content or "@injectable" in content, "Helper must have @injectable"
    assert "infrastructure" in content.lower(), "Helper must mention infrastructure-only restriction"
