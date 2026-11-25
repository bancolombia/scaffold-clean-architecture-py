"""Tests for DrivenAdapterPsycopg factory."""

from __future__ import annotations

import tomllib
from pathlib import Path

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.factory.driven_adapters.da_psycopg import DrivenAdapterPsycopg
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject

_SRC = Path("src") / "ms_demo" / "infrastructure" / "driven_adapters" / "psycopg"
_TESTS = Path("src") / "tests" / "infrastructure" / "driven_adapters" / "psycopg"


def _builder(root: Path, *, dry_run: bool) -> ModuleBuilder:
    project = ProjectContext(name="ms-demo")
    return ModuleBuilder(
        project_root=root,
        project_ctx=project,
        module_ctx=ModuleContext(name="psycopg", project=project),
        dry_run=dry_run,
    )


def _pyproject(root: Path) -> dict[str, object]:
    with (root / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _runtime(root: Path) -> list[str]:
    project = _pyproject(root)["project"]
    assert isinstance(project, dict)
    return [d for d in project.get("dependencies", []) if isinstance(d, str)]


def test_psycopg_files_queued_in_dry_run(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    builder = _builder(tmp_path, dry_run=True)

    DrivenAdapterPsycopg().build(builder)
    preview = builder.persist()

    for rel in (
        _SRC / "__init__.py",
        _SRC / "psycopg_settings.py",
        _SRC / "psycopg_config.py",
        _SRC / "psycopg_repository.py",
        _TESTS / "test_psycopg_adapter.py",
        Path("src") / "tests" / "conftest.py",
    ):
        assert tmp_path / rel in preview, f"missing {rel}"


def test_psycopg_runtime_dependencies_without_extra_groups(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
    before = _pyproject(tmp_path)["dependency-groups"]
    builder = _builder(tmp_path, dry_run=False)

    DrivenAdapterPsycopg().build(builder)
    builder.persist()

    runtime = _runtime(tmp_path)
    assert any(d.startswith("psycopg[binary]") for d in runtime)
    assert any(d.startswith("psycopg-pool") for d in runtime)
    assert any(d.startswith("pydantic-settings") for d in runtime)
    assert _pyproject(tmp_path)["dependency-groups"] == before


def test_psycopg_conftest_fixture_appended(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    builder = _builder(tmp_path, dry_run=False)

    DrivenAdapterPsycopg().build(builder)
    builder.persist()

    content = (tmp_path / "src" / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "def psycopg_env(" in content
    assert "PSYCOPG_DATABASE_URL" in content


def test_psycopg_pool_added_when_psycopg_binary_already_declared(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace("dependencies = []", 'dependencies = ["psycopg[binary]~=3.3.9"]'),
        encoding="utf-8",
    )
    builder = _builder(tmp_path, dry_run=False)

    DrivenAdapterPsycopg().build(builder)
    builder.persist()

    runtime = _runtime(tmp_path)
    assert sum(d.startswith("psycopg[") for d in runtime) == 1
    assert any(d.startswith("psycopg-pool") for d in runtime)


def test_psycopg_gateway_binds_repository_and_appends_wiring_test(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    builder = _builder(tmp_path, dry_run=False)
    builder.add_param(
        "gateway",
        {"name": "book_repository", "class_name": "BookRepository", "model_module": "book"},
    )

    DrivenAdapterPsycopg().build(builder)
    builder.persist()

    repo = (tmp_path / _SRC / "psycopg_repository.py").read_text(encoding="utf-8")
    assert "@wireup.injectable(as_type=BookRepository)" in repo
    assert "class PsycopgRepository(BookRepository)" in repo
    wiring = tmp_path / "src" / "tests" / "application" / "config" / "test_wiring.py"
    assert "async def test_container_resolves_psycopg(" in wiring.read_text(encoding="utf-8")
