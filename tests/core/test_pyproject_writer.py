"""Tests for pyproject_writer: inject_dependencies, inject_group_dependencies, update_project_scripts."""

import tomllib
from pathlib import Path

import pytest

from scaffold_ca_python.core.pyproject_writer import (
    inject_dependencies,
    inject_group_dependencies,
    update_project_scripts,
)
from scaffold_ca_python.models.context import ProjectContext

# Fixtures


def _make_pyproject(tmp_path: Path, deps: list[str] | None = None) -> Path:
    """Write a minimal pyproject.toml with optional pre-existing dependencies."""
    existing = deps if deps is not None else []
    deps_toml = "\n".join(f'    "{d}",' for d in existing)
    content = f"""\
[project]
name = "my-project"
dependencies = [
{deps_toml}
]

[tool.scaffold-ca-python]
name = "MyProject"
"""
    path = tmp_path / "pyproject.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _make_pyproject_no_deps(tmp_path: Path) -> Path:
    """Write a pyproject.toml with no [project.dependencies] key at all."""
    content = """\
[project]
name = "my-project"

[tool.scaffold-ca-python]
name = "MyProject"
"""
    path = tmp_path / "pyproject.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _read_deps(pyproject: Path) -> list[str]:
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    return data.get("project", {}).get("dependencies", [])


# inject_dependencies — writes


def test_inject_adds_new_package(tmp_path: Path) -> None:
    pyproject = _make_pyproject(tmp_path)
    added = inject_dependencies(tmp_path, ["fastapi>=0.100"])
    assert added == ["fastapi>=0.100"]
    assert any("fastapi" in d for d in _read_deps(pyproject))


def test_inject_adds_multiple_packages(tmp_path: Path) -> None:
    pyproject = _make_pyproject(tmp_path)
    added = inject_dependencies(tmp_path, ["fastapi>=0.100", "uvicorn[standard]>=0.20"])
    assert len(added) == 2
    deps = _read_deps(pyproject)
    assert any("fastapi" in d for d in deps)
    assert any("uvicorn" in d for d in deps)


def test_inject_skips_duplicate_by_name_prefix(tmp_path: Path) -> None:
    _make_pyproject(tmp_path, deps=["fastapi>=0.100"])
    added = inject_dependencies(tmp_path, ["fastapi>=0.100"])
    assert added == []
    # still only one fastapi entry
    assert sum(1 for d in _read_deps(tmp_path / "pyproject.toml") if "fastapi" in d) == 1


def test_inject_skips_duplicate_with_extras(tmp_path: Path) -> None:
    _make_pyproject(tmp_path, deps=["uvicorn[standard]>=0.20"])
    added = inject_dependencies(tmp_path, ["uvicorn[standard]>=0.20"])
    assert added == []


def test_inject_partial_list_only_adds_missing(tmp_path: Path) -> None:
    _make_pyproject(tmp_path, deps=["fastapi>=0.100"])
    added = inject_dependencies(tmp_path, ["fastapi>=0.100", "httpx>=0.27"])
    assert added == ["httpx>=0.27"]


def test_inject_returns_empty_when_all_present(tmp_path: Path) -> None:
    _make_pyproject(tmp_path, deps=["fastapi>=0.100", "httpx>=0.27"])
    added = inject_dependencies(tmp_path, ["fastapi>=0.100", "httpx>=0.27"])
    assert added == []


def test_inject_dedupes_across_operators(tmp_path: Path) -> None:
    _make_pyproject(tmp_path, deps=["dependency-injector==4.49.1"])
    added = inject_dependencies(tmp_path, ["dependency-injector~=4.49.1"])
    assert added == []


def test_inject_creates_dependencies_key_when_absent(tmp_path: Path) -> None:
    _make_pyproject_no_deps(tmp_path)
    added = inject_dependencies(tmp_path, ["httpx>=0.27"])
    assert added == ["httpx>=0.27"]
    assert any("httpx" in d for d in _read_deps(tmp_path / "pyproject.toml"))


def test_inject_with_empty_packages_list_returns_empty(tmp_path: Path) -> None:
    _make_pyproject(tmp_path)
    added = inject_dependencies(tmp_path, [])
    assert added == []


def test_inject_preserves_existing_dependencies(tmp_path: Path) -> None:
    _make_pyproject(tmp_path, deps=["pydantic>=2.0", "rich>=14.0"])
    inject_dependencies(tmp_path, ["httpx>=0.27"])
    deps = _read_deps(tmp_path / "pyproject.toml")
    assert any("pydantic" in d for d in deps)
    assert any("rich" in d for d in deps)
    assert any("httpx" in d for d in deps)


# dry_run_inject — never writes


def test_dry_run_returns_packages_that_would_be_added(tmp_path: Path) -> None:
    _make_pyproject(tmp_path)
    would_add = inject_dependencies(tmp_path, ["fastapi>=0.100", "uvicorn[standard]>=0.20"], dry_run=True)
    assert would_add == ["fastapi>=0.100", "uvicorn[standard]>=0.20"]


def test_dry_run_never_writes_to_disk(tmp_path: Path) -> None:
    pyproject = _make_pyproject(tmp_path)
    original = pyproject.read_bytes()
    inject_dependencies(tmp_path, ["fastapi>=0.100"], dry_run=True)
    assert pyproject.read_bytes() == original


def test_dry_run_skips_already_present_packages(tmp_path: Path) -> None:
    _make_pyproject(tmp_path, deps=["fastapi>=0.100"])
    would_add = inject_dependencies(tmp_path, ["fastapi>=0.100"], dry_run=True)
    assert would_add == []


def test_dry_run_with_empty_packages_returns_empty(tmp_path: Path) -> None:
    _make_pyproject(tmp_path)
    would_add = inject_dependencies(tmp_path, [], dry_run=True)
    assert would_add == []


# Error handling


def test_malformed_toml_raises_on_inject(tmp_path: Path) -> None:
    bad = tmp_path / "pyproject.toml"
    bad.write_text("this is not valid toml ][", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        inject_dependencies(tmp_path, ["fastapi>=0.100"])


def test_missing_pyproject_raises_on_inject(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inject_dependencies(tmp_path, ["fastapi>=0.100"])


# update_project_scripts


def _make_pyproject_with_scripts(tmp_path: Path, entry: str) -> Path:
    """Write a minimal pyproject.toml with a [project.scripts] entry."""
    content = f"""\
[project]
name = "my_app"

[project.scripts]
my-app = "{entry}"

[tool.scaffold-ca-python]
name = "MyApp"
python_package = "my_app"
"""
    path = tmp_path / "pyproject.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _make_pyproject_without_scripts(tmp_path: Path) -> Path:
    """Write a minimal pyproject.toml with no [project.scripts] section."""
    content = """\
[project]
name = "my_app"

[tool.scaffold-ca-python]
name = "MyApp"
python_package = "my_app"
"""
    path = tmp_path / "pyproject.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _read_scripts(pyproject: Path) -> dict[str, str]:
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    return data.get("project", {}).get("scripts", {})


def test_update_project_scripts_changes_entry(tmp_path: Path) -> None:
    """updates main:main → server:start_server and returns True."""
    pyproject = _make_pyproject_with_scripts(tmp_path, "my_app.main:main")
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"))
    assert result is True
    assert _read_scripts(pyproject)["my-app"] == "my_app.server:start_server"


def test_update_project_scripts_is_idempotent(tmp_path: Path) -> None:
    """second call returns False and leaves entry unchanged."""
    pyproject = _make_pyproject_with_scripts(tmp_path, "my_app.server:start_server")
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"), entry_fn="start_server")
    assert result is False
    assert _read_scripts(pyproject)["my-app"] == "my_app.server:start_server"


def test_update_project_scripts_creates_section_when_absent(tmp_path: Path) -> None:
    """creates [project.scripts] when missing and writes correct entry."""
    pyproject = _make_pyproject_without_scripts(tmp_path)
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"))
    assert result is True
    assert _read_scripts(pyproject)["my-app"] == "my_app.server:start_server"


# dry_run_scripts_update — never writes


def test_dry_run_scripts_update_returns_true_when_change_needed(tmp_path: Path) -> None:
    """returns True (change needed) but does NOT write to disk."""
    pyproject = _make_pyproject_with_scripts(tmp_path, "my_app.main:main")
    original = pyproject.read_bytes()
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"), dry_run=True)
    assert result is True
    assert pyproject.read_bytes() == original


def test_dry_run_scripts_update_returns_false_when_already_correct(tmp_path: Path) -> None:
    """returns False when entry already matches server:start_server."""
    _make_pyproject_with_scripts(tmp_path, "my_app.server:start_server")
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"), entry_fn="start_server", dry_run=True)
    assert result is False


def test_dry_run_scripts_update_never_writes_to_disk(tmp_path: Path) -> None:
    """raw file bytes are identical before and after the call."""
    pyproject = _make_pyproject_with_scripts(tmp_path, "my_app.main:main")
    before = pyproject.read_bytes()
    update_project_scripts(tmp_path, ProjectContext(name="my-app"), dry_run=True)
    assert pyproject.read_bytes() == before


# inject_group_dependencies — writes


def _make_pyproject_with_dep_groups(tmp_path: Path, *, test: list[str] | None = None) -> Path:
    """Write a pyproject.toml with [dependency-groups] optionally pre-populated."""
    test_entries = "\n".join(f'    "{d}",' for d in (test or []))
    content = f"""\
[project]
name = "my-project"
dependencies = []

[dependency-groups]
test = [
{test_entries}
]
dev = [
    "ruff==0.16.8",
    {{include-group = "test"}},
]

[tool.scaffold-ca-python]
name = "MyProject"
"""
    path = tmp_path / "pyproject.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _read_group(pyproject: Path, group: str) -> list[str]:
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    entries = data.get("dependency-groups", {}).get(group, [])
    return [e for e in entries if isinstance(e, str)]


def test_inject_group_adds_new_package(tmp_path: Path) -> None:
    pyproject = _make_pyproject_with_dep_groups(tmp_path)
    added = inject_group_dependencies(tmp_path, "test", ["respx>=0.22"])
    assert added == ["respx>=0.22"]
    assert "respx>=0.22" in _read_group(pyproject, "test")


def test_inject_group_skips_duplicate(tmp_path: Path) -> None:
    _make_pyproject_with_dep_groups(tmp_path, test=["respx>=0.22"])
    added = inject_group_dependencies(tmp_path, "test", ["respx>=0.22"])
    assert added == []


def test_inject_group_skips_duplicate_by_name_prefix(tmp_path: Path) -> None:
    _make_pyproject_with_dep_groups(tmp_path, test=["respx==0.21.0"])
    added = inject_group_dependencies(tmp_path, "test", ["respx>=0.22"])
    assert added == []


def test_inject_group_creates_group_when_absent(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "my-project"\n', encoding="utf-8")
    added = inject_group_dependencies(tmp_path, "test", ["respx>=0.22"])
    assert added == ["respx>=0.22"]
    assert "respx>=0.22" in _read_group(pyproject, "test")


def test_inject_group_preserves_include_group_entries(tmp_path: Path) -> None:
    """include-group dicts in [dev] must survive the round-trip."""
    pyproject = _make_pyproject_with_dep_groups(tmp_path)
    inject_group_dependencies(tmp_path, "test", ["respx>=0.22"])
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    dev_entries = data.get("dependency-groups", {}).get("dev", [])
    include_entries = [e for e in dev_entries if isinstance(e, dict)]
    assert any(e.get("include-group") == "test" for e in include_entries), (
        "include-group entry was lost after inject_group_dependencies"
    )


def test_inject_group_multiple_packages(tmp_path: Path) -> None:
    pyproject = _make_pyproject_with_dep_groups(tmp_path)
    added = inject_group_dependencies(tmp_path, "test", ["respx>=0.22", "pytest-mock>=3.0"])
    assert added == ["respx>=0.22", "pytest-mock>=3.0"]
    group = _read_group(pyproject, "test")
    assert "respx>=0.22" in group
    assert "pytest-mock>=3.0" in group


# dry_run_group_inject — never writes


def test_dry_run_group_returns_packages_that_would_be_added(tmp_path: Path) -> None:
    _make_pyproject_with_dep_groups(tmp_path)
    would_add = inject_group_dependencies(tmp_path, "test", ["respx>=0.22"], dry_run=True)
    assert would_add == ["respx>=0.22"]


def test_dry_run_group_never_writes_to_disk(tmp_path: Path) -> None:
    pyproject = _make_pyproject_with_dep_groups(tmp_path)
    original = pyproject.read_bytes()
    inject_group_dependencies(tmp_path, "test", ["respx>=0.22"], dry_run=True)
    assert pyproject.read_bytes() == original


def test_dry_run_group_skips_already_present_packages(tmp_path: Path) -> None:
    _make_pyproject_with_dep_groups(tmp_path, test=["respx>=0.22"])
    would_add = inject_group_dependencies(tmp_path, "test", ["respx>=0.22"], dry_run=True)
    assert would_add == []


# entry_fn parameter — custom entry function ( additions from 019 tasks)


def test_update_project_scripts_default_uses_start_server(tmp_path: Path) -> None:
    """Default entry_fn='start_server' preserves existing behaviour."""
    pyproject = _make_pyproject_with_scripts(tmp_path, "my_app.main:main")
    update_project_scripts(tmp_path, ProjectContext(name="my-app"))
    assert _read_scripts(pyproject)["my-app"] == "my_app.server:start_server"


def test_update_project_scripts_custom_entry_fn_writes_main(tmp_path: Path) -> None:
    """entry_fn='main' writes <pkg>.server:main (used by MCP entry point)."""
    pyproject = _make_pyproject_with_scripts(tmp_path, "my_app.main:main")
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"), entry_fn="main")
    assert result is True
    assert _read_scripts(pyproject)["my-app"] == "my_app.server:main"


def test_update_project_scripts_custom_entry_fn_is_idempotent(tmp_path: Path) -> None:
    """Second call with entry_fn='main' returns False when entry already correct."""
    pyproject = _make_pyproject_with_scripts(tmp_path, "my_app.server:main")
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"), entry_fn="main")
    assert result is False
    assert _read_scripts(pyproject)["my-app"] == "my_app.server:main"


def test_dry_run_scripts_update_default_uses_start_server(tmp_path: Path) -> None:
    """Default entry_fn='start_server' in dry_run preserves existing behaviour."""
    _make_pyproject_with_scripts(tmp_path, "my_app.server:start_server")
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"), dry_run=True)
    assert result is False


def test_dry_run_scripts_update_custom_entry_fn_detects_change(tmp_path: Path) -> None:
    """entry_fn='main' returns True when entry is currently start_server."""
    pyproject = _make_pyproject_with_scripts(tmp_path, "my_app.server:start_server")
    original = pyproject.read_bytes()
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"), entry_fn="main", dry_run=True)
    assert result is True
    assert pyproject.read_bytes() == original  # never wrote to disk


def test_dry_run_scripts_update_custom_entry_fn_no_change_needed(tmp_path: Path) -> None:
    """entry_fn='main' returns False when entry already equals <pkg>.server:main."""
    _make_pyproject_with_scripts(tmp_path, "my_app.server:main")
    result = update_project_scripts(tmp_path, ProjectContext(name="my-app"), entry_fn="main", dry_run=True)
    assert result is False
