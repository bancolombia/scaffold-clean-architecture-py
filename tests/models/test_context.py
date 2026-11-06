"""Tests for ProjectContext and ModuleContext Pydantic models."""

import pytest
from pydantic import ValidationError

from scaffold_ca_python.models.context import ModuleContext, ProjectContext

# ProjectContext


def test_project_context_valid() -> None:
    ctx = ProjectContext(name="my-project")
    assert ctx.name == "my-project"
    assert ctx.python_package == "my_project"


def test_project_context_python_package_derived_from_name() -> None:
    ctx = ProjectContext(name="my-project")
    assert ctx.python_package == "my_project"


def test_project_context_python_package_with_numbers() -> None:
    ctx = ProjectContext(name="project2025")
    assert ctx.python_package == "project2025"


def test_project_context_name_must_start_with_letter() -> None:
    with pytest.raises(ValidationError):
        ProjectContext(name="1Invalid")


def test_project_context_name_rejects_spaces() -> None:
    with pytest.raises(ValidationError):
        ProjectContext(name="My Project")


def test_project_context_name_accepts_hyphens() -> None:
    ctx = ProjectContext(name="my-project")
    assert ctx.python_package == "my_project"


def test_project_context_name_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        ProjectContext(name="")


def test_project_context_name_allows_underscores() -> None:
    ctx = ProjectContext(name="my_project")
    assert ctx.name == "my_project"


def test_project_context_src_pkg_root() -> None:
    from pathlib import Path

    root = Path("/tmp/my-app")
    ctx = ProjectContext(name="my-app", project_root=root)
    assert ctx.src_pkg_root == root / "src" / "my_app"


# ModuleContext


def _make_project() -> ProjectContext:
    return ProjectContext(name="my-project")


def test_module_context_valid() -> None:
    ctx = ModuleContext(name="order", project=_make_project())
    assert ctx.name == "order"


def test_module_context_class_name_is_pascal_case() -> None:
    ctx = ModuleContext(name="my_order", project=_make_project())
    assert ctx.class_name == "MyOrder"


def test_module_context_module_name_is_snake_case() -> None:
    ctx = ModuleContext(name="my-order", project=_make_project())
    assert ctx.module_name == "my_order"


def test_module_context_name_must_start_with_letter() -> None:
    with pytest.raises(ValidationError):
        ModuleContext(name="1Order", project=_make_project())


def test_module_context_name_rejects_spaces() -> None:
    with pytest.raises(ValidationError):
        ModuleContext(name="My Order", project=_make_project())
