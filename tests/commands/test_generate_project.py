"""Tests for ca / generate-project command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.helpers import strip_ansi

runner = CliRunner()

# Success path


def test_creates_project_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (tmp_path / "my-project").is_dir()


def test_success_message_uses_directory_name_not_snake_pkg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "my-project/" in result.output
    assert "my_project/" not in result.output


def test_creates_all_layer_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    assert result.exit_code == 0
    root = tmp_path / "my-project"
    assert (root / "src" / "my_project" / "application" / "__init__.py").exists()
    assert (root / "src" / "my_project" / "domain" / "model" / "__init__.py").exists()
    assert (root / "src" / "my_project" / "domain" / "usecase" / "__init__.py").exists()
    assert (root / "src" / "my_project" / "infrastructure" / "driven_adapters" / "__init__.py").exists()
    assert (root / "src" / "my_project" / "infrastructure" / "entry_points" / "__init__.py").exists()
    assert (root / "src" / "my_project" / "infrastructure" / "helpers" / "__init__.py").exists()


def test_creates_config_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    assert result.exit_code == 0
    root = tmp_path / "my-project"
    assert (root / "pyproject.toml").exists()
    assert (root / "README.md").exists()
    assert (root / ".gitignore").exists()
    assert (root / "mypy.ini").exists()
    # : Docker and Python version files
    assert (root / "Dockerfile").exists()
    assert (root / ".dockerignore").exists()
    assert (root / ".python-version").exists()
    # : No .ruff.toml
    assert not (root / ".ruff.toml").exists()


def test_python_version_file_contains_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / ".python-version").read_text()
    assert "3.13" in content


def test_pyproject_has_ruff_lint_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert "[tool.ruff.lint]" in content


def test_creates_di_config_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    assert result.exit_code == 0
    cfg = tmp_path / "my-project" / "src" / "my_project" / "application" / "config"
    assert (cfg / "__init__.py").exists()
    assert (cfg / "config.py").exists()
    assert (cfg / "wiring.py").exists()
    assert (cfg / "usecases" / "__init__.py").exists()


def test_pyproject_has_di_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert "wireup" in content
    assert "pydantic-settings" in content


def test_creates_main_py(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    assert result.exit_code == 0
    main_py = tmp_path / "my-project" / "src" / "my_project" / "main.py"
    assert main_py.exists()
    content = main_py.read_text()
    assert "def main" in content


def test_pyproject_has_scripts_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert "[project.scripts]" in content
    assert "my_project.main:main" in content


def test_pyproject_contains_scaffold_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert "[tool.scaffold-ca-python]" in content
    assert "my-project" in content


def test_package_flag_is_not_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "simple-app", "--package", "com.example"])
    assert result.exit_code != 0


# : clean-architecture command


def test_clean_architecture_creates_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["clean-architecture", "--name", "demo"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (tmp_path / "demo").is_dir()


def test_clean_architecture_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["clean-architecture", "--dry-run", "--name", "demo"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (tmp_path / "demo").exists()


def test_clean_architecture_help_contains_options() -> None:
    result = runner.invoke(app, ["clean-architecture", "--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "--name" in output
    assert "--dry-run" in output


def test_ca_help_identical_to_clean_architecture_help() -> None:
    """ca --help must match clean-architecture --help in all content.

    The Usage line inherently shows the invoked command name (Typer behaviour),
    so we normalise that line before comparing.
    """
    r_ca = runner.invoke(app, ["ca", "--help"])
    r_clean = runner.invoke(app, ["clean-architecture", "--help"])

    def _normalise(output: str) -> str:
        # Clean ANSI codes first
        output = strip_ansi(output)
        lines = output.splitlines()
        return "\n".join(
            line.replace(" ca ", " <CMD> ").replace(" clean-architecture ", " <CMD> ").rstrip()
            if "Usage:" in line
            else line.rstrip()
            for line in lines
        )

    assert _normalise(r_ca.output) == _normalise(r_clean.output)


# : ca alias and generate-project tombstone


def test_ca_alias_creates_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "demo"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (tmp_path / "demo").is_dir()


def test_creates_tests_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    assert (tmp_path / "my-project" / "src" / "tests" / "__init__.py").exists()


def test_ca_creates_src_tests_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    assert (tmp_path / "my-project" / "src" / "tests" / "__init__.py").exists()
    assert not (tmp_path / "my-project" / "tests").exists()


def test_ca_dry_run_shows_src_tests_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project", "--dry-run"], catch_exceptions=False)
    assert "src/tests/__init__.py" in result.output
    assert result.output.count("tests/__init__.py") == result.output.count("src/tests/__init__.py")


# Dry-run


def test_dry_run_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "dry-project", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (tmp_path / "dry-project").exists()
    assert not any(tmp_path.iterdir())


def test_dry_run_prints_file_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "dry-project", "--dry-run"], catch_exceptions=False)
    assert "pyproject.toml" in result.output or "dry-project" in result.output


def test_dry_run_header_uses_original_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dry-run tree header must show the original name (e.g. 'my-project/'), not the snake_case package."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    # The root label in the tree must use the original name, not python_pkg (snake_case).
    first_line = result.output.strip().splitlines()[0]
    assert "my-project" in first_line, f"Expected 'my-project' in first line, got: {first_line!r}"


# Error cases


def test_duplicate_project_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    result = runner.invoke(app, ["ca", "--name", "my-project"])
    assert result.exit_code == 1


def test_invalid_name_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "1InvalidName"])
    assert result.exit_code != 0


def test_pascal_case_name_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "MyProject"])
    assert result.exit_code == 1
    assert "kebab-case" in result.output


def test_kebab_name_generates_snake_case_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-project", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    for line in result.output.splitlines():
        stripped = line.strip()
        if stripped.endswith(".py"):
            stem = stripped.split("/")[-1][:-3]
            assert stem == stem.lower() and "-" not in stem


# : injection test — renderer and writer are used when injected

#  (028): wireup project layout (must FAIL before -)


def test_ca_generates_wiring_py(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ca must generate wiring.py instead of *_container.py files."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    cfg = tmp_path / "my-project" / "src" / "my_project" / "application" / "config"
    assert (cfg / "wiring.py").exists(), "wiring.py not found"


def test_ca_generates_usecases_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ca must generate application/config/usecases/__init__.py."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    usecases_init = (
        tmp_path / "my-project" / "src" / "my_project" / "application" / "config" / "usecases" / "__init__.py"
    )
    assert usecases_init.exists(), "usecases/__init__.py not found"


def test_ca_does_not_generate_container_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ca must NOT generate *_container.py files for wireup projects."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    cfg = tmp_path / "my-project" / "src" / "my_project" / "application" / "config"
    for forbidden in ("container.py", "resource_container.py", "driven_adapters_container.py", "usecases_container.py"):
        assert not (cfg / forbidden).exists(), f"Found unexpected legacy file: {forbidden}"


def test_ca_pyproject_has_wireup_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Generated pyproject.toml must declare wireup (not dependency-injector)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert "wireup" in content, "wireup dependency not found"
    assert "dependency-injector" not in content, "legacy dependency still present"


def test_ca_pyproject_has_scaffold_version_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """generated pyproject.toml must contain scaffold_version in [tool.scaffold-ca-python]."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert "scaffold_version = " in content, "scaffold_version key not found in pyproject"
    assert 'di = "wireup"' not in content, "legacy di key must not be present"


def test_ca_pyproject_has_ruff_async_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """generated pyproject.toml must enable ruff ASYNC rule."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert "ASYNC" in content, "ruff ASYNC rule not found"


def test_ca_pyproject_has_asyncio_mode_auto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """generated pyproject.toml must set asyncio_mode = 'auto' in pytest config."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert 'asyncio_mode = "auto"' in content, "asyncio_mode = 'auto' not found"


def test_ca_pyproject_disables_tc_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """generated pyproject.toml must disable ruff TC rule to keep Injected/Inject at runtime."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    content = (tmp_path / "my-project" / "pyproject.toml").read_text()
    assert "TC" in content, "TC rule ignore not found"


# : injection test — renderer and writer are used when injected


def test_generate_project_uses_injected_renderer_and_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_generate_project_impl must pass renderer/writer to ModuleBuilder."""
    monkeypatch.chdir(tmp_path)
    from scaffold_ca_python.commands.generate_project import _generate_project_impl

    class FakeRenderer:
        called = False

        def render(self, template: str, ctx: object) -> str:
            FakeRenderer.called = True
            return "# fake"

    class FakeWriter:
        called = False

        def write(self, path: object, content: str) -> None:
            FakeWriter.called = True

        def delete(self, path: object) -> None:
            pass

    _generate_project_impl("my-test-app", dry_run=False, renderer=FakeRenderer(), writer=FakeWriter())  # type: ignore[arg-type]

    assert FakeRenderer.called, "Expected the injected renderer to be called"
    assert FakeWriter.called, "Expected the injected writer to be called"


# : wiring.py uses injectables= (not deprecated service_modules=)


def test_wiring_uses_injectables_param(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """generated wiring.py must use create_async_container(injectables=...) not service_modules=."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-project"], catch_exceptions=False)
    wiring_path = tmp_path / "my-project" / "src" / "my_project" / "application" / "config" / "wiring.py"
    assert wiring_path.exists(), "wiring.py must exist after ca"
    content = wiring_path.read_text()
    assert "injectables=" in content, "wiring.py must use injectables= param (not deprecated service_modules=)"
    assert "service_modules=" not in content, "wiring.py must not use deprecated service_modules= param"
