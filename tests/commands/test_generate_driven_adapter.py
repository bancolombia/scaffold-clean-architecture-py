"""Tests for gda / generate-driven-adapter command."""

from pathlib import Path

from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.helpers import strip_ansi

runner = CliRunner()

# Fixtures

# rest-consumer type


def test_rest_consumer_impl_contains_httpx(project_root: Path) -> None:
    runner.invoke(app, ["gda", "--type", "rest-consumer"], catch_exceptions=False)
    content = (
        project_root / "src" / "my_app" / "infrastructure" / "driven_adapters" / "rest_consumer" / "rest_consumer.py"
    ).read_text()
    assert "httpx" in content


# sqlalchemy type


def test_sqlalchemy_impl_contains_create_async_engine(project_root: Path) -> None:
    runner.invoke(app, ["gda", "--type", "sqlalchemy"], catch_exceptions=False)
    content = (
        project_root / "src" / "my_app" / "infrastructure" / "driven_adapters" / "sqlalchemy" / "sqlalchemy_config.py"
    ).read_text()
    assert "create_async_engine" in content


def test_sqlalchemy_injects_sqlalchemy_and_psycopg_binary(project_root: Path) -> None:
    import tomllib

    runner.invoke(app, ["gda", "--type", "sqlalchemy"], catch_exceptions=False)
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    runtime: list[str] = data.get("project", {}).get("dependencies", [])
    test_group: list[str] = data.get("dependency-groups", {}).get("test", [])
    assert any("sqlalchemy" in d and "asyncio" in d for d in runtime)
    assert any("psycopg" in d for d in runtime), "psycopg[binary] must be in runtime for default driver"
    assert not any("aiosqlite" in d for d in runtime), "aiosqlite must NOT be in runtime for default driver"
    assert any("aiosqlite" in d for d in test_group if isinstance(d, str)), "aiosqlite must be in test group"


def test_dry_run_prints_sqlalchemy_paths(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "sqlalchemy", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    out = strip_ansi(result.output)
    assert "sqlalchemy_config" in out
    assert "driven_adapters/sqlalchemy" in out


# secrets type


# generic type


def test_generic_impl_contains_class_name(project_root: Path) -> None:
    runner.invoke(app, ["gda", "--type", "generic", "--name", "cache_store"], catch_exceptions=False)
    content = (
        project_root / "src" / "my_app" / "infrastructure" / "driven_adapters" / "cache_store" / "adapter.py"
    ).read_text()
    assert "CacheStore" in content


# Alias


def test_generate_driven_adapter_alias_works(project_root: Path) -> None:
    result = runner.invoke(app, ["generate-driven-adapter", "--type", "rest-consumer"], catch_exceptions=False)
    assert result.exit_code == 0


# Dry-run


def test_dry_run_writes_nothing_rest_consumer(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "rest-consumer", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (
        project_root / "src" / "my_app" / "infrastructure" / "driven_adapters" / "rest_consumer" / "rest_consumer.py"
    ).exists()


def test_dry_run_prints_paths(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "rest-consumer", "--dry-run"], catch_exceptions=False)
    assert "rest_consumer" in result.output


def test_dry_run_generic_writes_nothing(project_root: Path) -> None:
    result = runner.invoke(
        app,
        ["gda", "--type", "generic", "--name", "cache_store", "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert not (
        project_root / "src" / "my_app" / "infrastructure" / "driven_adapters" / "cache_store" / "adapter.py"
    ).exists()


# Error cases


def test_generic_without_name_exits_1(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "generic"])
    assert result.exit_code == 1
    assert "--name" in result.output


def test_unknown_type_exits_1(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "kafka"])
    assert result.exit_code == 1
    assert "kafka" in result.output.lower() or "Unknown" in result.output


def test_duplicate_adapter_dir_exits_1(project_root: Path) -> None:
    runner.invoke(app, ["gda", "--type", "rest-consumer"], catch_exceptions=False)
    result = runner.invoke(app, ["gda", "--type", "rest-consumer"])
    assert result.exit_code == 1


# : Auto-inject dependencies


def test_rest_consumer_injects_httpx(project_root: Path) -> None:
    import tomllib

    runner.invoke(app, ["gda", "--type", "rest-consumer"], catch_exceptions=False)
    content = (project_root / "pyproject.toml").read_text()
    assert "httpx" in content

    # respx must be in [dependency-groups.test], not in runtime deps
    with (project_root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    runtime: list[str] = data.get("project", {}).get("dependencies", [])
    assert not any("respx" in d for d in runtime), "respx must not be in runtime deps"
    test_entries = [e for e in data.get("dependency-groups", {}).get("test", []) if isinstance(e, str)]
    assert any("respx" in e for e in test_entries), f"respx not found in [dependency-groups.test]: {test_entries}"


def test_secrets_injects_boto3(project_root: Path) -> None:
    runner.invoke(app, ["gda", "--type", "secrets"], catch_exceptions=False)
    content = (project_root / "pyproject.toml").read_text()
    assert "boto3" in content


def test_generic_injects_nothing(project_root: Path) -> None:
    original = (project_root / "pyproject.toml").read_text()
    runner.invoke(app, ["gda", "--type", "generic", "--name", "cache_store"], catch_exceptions=False)
    assert (project_root / "pyproject.toml").read_text() == original


def test_rest_consumer_inject_is_idempotent(project_root: Path) -> None:
    runner.invoke(app, ["gda", "--type", "rest-consumer"], catch_exceptions=False)
    import shutil

    shutil.rmtree(project_root / "src" / "my_app" / "infrastructure" / "driven_adapters" / "rest_consumer")
    shutil.rmtree(
        project_root / "src" / "tests" / "infrastructure" / "driven_adapters" / "rest_consumer",
        ignore_errors=True,
    )
    runner.invoke(app, ["gda", "--type", "rest-consumer"], catch_exceptions=False)
    content = (project_root / "pyproject.toml").read_text()
    assert content.count("httpx~=") == 1, "httpx must appear exactly once as a dependency (not duplicated)"
    assert content.count("respx~=") == 1, "respx must appear exactly once as a dependency (not duplicated)"


def test_dry_run_does_not_inject_deps(project_root: Path) -> None:
    original = (project_root / "pyproject.toml").read_text()
    runner.invoke(app, ["gda", "--type", "rest-consumer", "--dry-run"], catch_exceptions=False)
    assert (project_root / "pyproject.toml").read_text() == original


def test_dry_run_prints_deps_to_inject(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "rest-consumer", "--dry-run"], catch_exceptions=False)
    assert "httpx" in result.output
    assert "respx" in result.output
    # The bracket labels must render literally (not swallowed as Rich markup).
    assert "[project.dependencies]" in result.output
    assert "[dependency-groups.test]" in result.output


# : gda --help epilog


def test_gda_help_shows_type_descriptions() -> None:
    result = runner.invoke(app, ["gda", "--help"])
    assert result.exit_code == 0
    assert "httpx" in result.output


def test_gda_help_notes_name_required_for_generic() -> None:
    result = runner.invoke(app, ["gda", "--help"])
    assert result.exit_code == 0
    assert "--name required" in strip_ansi(result.output)


def test_gda_help_contains_custom_adapter_description() -> None:
    result = runner.invoke(app, ["gda", "--help"])
    assert result.exit_code == 0
    assert "Custom adapter" in result.output


# : no-args → help

# dry-run shows sqlalchemy_models path


def test_dry_run_prints_sqlalchemy_models_path(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "sqlalchemy", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    out = strip_ansi(result.output)
    assert "sqlalchemy_models" in out


# conftest idempotency


def test_sqlalchemy_conftest_idempotent(project_root: Path) -> None:
    """T012a: running gda --type sqlalchemy twice must not duplicate sqlalchemy_env."""
    runner.invoke(app, ["gda", "--type", "sqlalchemy"], catch_exceptions=False)
    # second invocation should fail (dir already exists) but conftest must still have only one fixture
    runner.invoke(app, ["gda", "--type", "sqlalchemy"])
    conftest = (project_root / "src" / "tests" / "conftest.py").read_text()
    assert conftest.count("sqlalchemy_env") == 1


# psycopg type


def test_dry_run_prints_psycopg_paths_and_pool_dependency(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "psycopg", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    out = strip_ansi(result.output)
    assert "driven_adapters/psycopg" in out
    assert "psycopg_config" in out
    assert "psycopg-pool" in out


def test_driver_flag_rejected_for_psycopg(project_root: Path) -> None:
    result = runner.invoke(app, ["gda", "--type", "psycopg", "--driver", "sqlite"])
    assert result.exit_code == 1
    assert "only valid with --type sqlalchemy" in strip_ansi(result.output)


def test_psycopg_conftest_idempotent(project_root: Path) -> None:
    runner.invoke(app, ["gda", "--type", "psycopg"], catch_exceptions=False)
    runner.invoke(app, ["gda", "--type", "psycopg"])
    conftest = (project_root / "src" / "tests" / "conftest.py").read_text()
    assert conftest.count("def psycopg_env(") == 1


def test_gda_help_lists_psycopg_with_example() -> None:
    result = runner.invoke(app, ["gda", "--help"])
    assert result.exit_code == 0
    out = strip_ansi(result.output)
    assert "psycopg" in out
    assert "--type psycopg --gateway" in out
