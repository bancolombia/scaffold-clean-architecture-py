"""Tests for DrivenAdapterSqlAlchemy factory."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext) -> ModuleContext:
    return ModuleContext(name="sqlalchemy", project=project)


def test_sqlalchemy_files_queued_in_dry_run(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=True,
    )

    from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

    DrivenAdapterSqlAlchemy().build(builder)
    preview = builder.persist()

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "driven_adapters" / "sqlalchemy"
    test_dir = tmp_path / "src" / "tests" / "infrastructure" / "driven_adapters" / "sqlalchemy"

    for expected in (
        src_dir / "__init__.py",
        src_dir / "sqlalchemy_settings.py",
        src_dir / "sqlalchemy_config.py",
        src_dir / "sqlalchemy_models.py",
        src_dir / "sqlalchemy_repository.py",
        test_dir / "test_sqlalchemy_adapter.py",
        tmp_path / "src" / "tests" / "conftest.py",
    ):
        assert expected in preview, f"missing {expected.relative_to(tmp_path)}"


def test_sqlalchemy_dependencies_injected(tmp_path: Path) -> None:
    import tomllib

    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=False,
    )

    from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

    DrivenAdapterSqlAlchemy().build(builder)
    builder.persist()

    with (tmp_path / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    runtime = data.get("project", {}).get("dependencies", [])
    runtime_str = [e for e in runtime if isinstance(e, str)]
    test_group = data.get("dependency-groups", {}).get("test", [])
    test_str = [e for e in test_group if isinstance(e, str)]
    assert any("sqlalchemy" in e and "asyncio" in e for e in runtime_str)
    assert any("psycopg" in e for e in runtime_str), "psycopg[binary] must be in runtime for default postgresql driver"
    assert not any("aiosqlite" in e for e in runtime_str), "aiosqlite must NOT be in runtime for postgresql driver"
    assert any("aiosqlite" in e for e in test_str), "aiosqlite must be in test group"


def test_sqlalchemy_driver_postgresql_adds_psycopg_binary(tmp_path: Path) -> None:
    import tomllib

    from scaffold_ca_python.commands.generate_driven_adapter import DbDriver

    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=False,
    )
    builder.add_param("driver", DbDriver.postgresql)

    from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

    DrivenAdapterSqlAlchemy().build(builder)
    builder.persist()

    with (tmp_path / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    runtime = data.get("project", {}).get("dependencies", [])
    assert any("psycopg" in e for e in runtime)
    assert not any("aiosqlite" in e for e in runtime)


def test_sqlalchemy_driver_sqlite_adds_aiosqlite_to_runtime(tmp_path: Path) -> None:
    import tomllib

    from scaffold_ca_python.commands.generate_driven_adapter import DbDriver

    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=False,
    )
    builder.add_param("driver", DbDriver.sqlite)

    from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

    DrivenAdapterSqlAlchemy().build(builder)
    builder.persist()

    with (tmp_path / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    runtime = data.get("project", {}).get("dependencies", [])
    assert any("aiosqlite" in e for e in runtime)
    assert not any("psycopg" in e for e in runtime)


def test_aiosqlite_always_in_test_group(tmp_path: Path) -> None:
    import tomllib

    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=False,
    )

    from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

    DrivenAdapterSqlAlchemy().build(builder)
    builder.persist()

    with (tmp_path / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    test_group = data.get("dependency-groups", {}).get("test", [])
    assert any("aiosqlite" in e for e in test_group if isinstance(e, str))


def test_sqlalchemy_conftest_fixture_appended(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=False,
    )

    from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

    DrivenAdapterSqlAlchemy().build(builder)
    builder.persist()

    conftest_path = tmp_path / "src" / "tests" / "conftest.py"
    assert conftest_path.exists()
    content = conftest_path.read_text(encoding="utf-8")
    assert "sqlalchemy_env" in content
    assert "SQLALCHEMY_DATABASE_URL" in content
    assert "sqlite+aiosqlite:///:memory:" in content


def test_sqlalchemy_gateway_renders_as_type(tmp_path: Path) -> None:
    from types import SimpleNamespace

    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=False,
    )
    builder.add_param(
        "gateway",
        SimpleNamespace(
            name="book_repository",
            class_name="BookRepository",
            model_module="book",
        ),
    )

    from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

    DrivenAdapterSqlAlchemy().build(builder)
    builder.persist()

    repo = (
        tmp_path / "src" / "ms_demo" / "infrastructure" / "driven_adapters" / "sqlalchemy" / "sqlalchemy_repository.py"
    )
    content = repo.read_text(encoding="utf-8")
    assert "@wireup.injectable(as_type=BookRepository)" in content
    assert "class SQLAlchemyRepository(BookRepository)" in content


def test_sqlalchemy_files_include_models_in_dry_run(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(
        project_root=tmp_path,
        project_ctx=project,
        module_ctx=_module_ctx(project),
        dry_run=True,
    )

    from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

    DrivenAdapterSqlAlchemy().build(builder)
    preview = builder.persist()

    models_path = (
        tmp_path / "src" / "ms_demo" / "infrastructure" / "driven_adapters" / "sqlalchemy" / "sqlalchemy_models.py"
    )
    assert models_path in preview, "sqlalchemy_models.py must be in dry-run preview"
