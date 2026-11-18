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
