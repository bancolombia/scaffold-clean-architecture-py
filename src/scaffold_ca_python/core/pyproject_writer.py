"""pyproject_writer: inject dependencies into [project.dependencies] in pyproject.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from scaffold_ca_python.models.context import ProjectContext


def _pyproject_path(project_root: Path) -> Path:
    return project_root / "pyproject.toml"


def _load(project_root: Path) -> dict[str, Any]:
    with _pyproject_path(project_root).open("rb") as fh:
        return tomllib.load(fh)


def _save(project_root: Path, data: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    with _pyproject_path(project_root).open("wb") as fh:
        tomli_w.dump(data, fh)


def _name_prefix(package: str) -> str:
    """Extract the bare package name, stripping version specifier and extras.

    Examples::

        "fastapi>=0.100"        -> "fastapi"
        "uvicorn[standard]>=0.20" -> "uvicorn"
        "a2a-sdk>=0.1"          -> "a2a-sdk"
        "boto3~=1.43.98"        -> "boto3"
    """
    name = package.split("~=")[0].split(">=")[0].split("==")[0].split("<")[0].split("!=")[0]
    name = name.split("[")[0]
    return name.strip().lower()


def _missing(existing: list[str], packages: list[str]) -> list[str]:
    """Return packages not already present in *existing* (by name prefix)."""
    existing_names = {_name_prefix(d) for d in existing}
    return [p for p in packages if _name_prefix(p) not in existing_names]


def inject_dependencies(project_root: Path, packages: list[str], *, dry_run: bool = False) -> list[str]:
    """Add *packages* to ``[project.dependencies]`` in ``pyproject.toml``.

    Idempotent: a package whose bare name is already present is skipped.
    Persists via ``tomli_w`` (the on-disk file may be normalized/reordered).

    When *dry_run* is ``True``, returns packages that would be added without writing.
    """
    data = _load(project_root)
    deps: list[str] = data.setdefault("project", {}).setdefault("dependencies", [])
    to_add = _missing(deps, packages)
    if not to_add:
        return []

    if not dry_run:
        deps.extend(to_add)
        _save(project_root, data, dry_run=False)

    return to_add


def inject_group_dependencies(
    project_root: Path,
    group: str,
    packages: list[str],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add *packages* to ``[dependency-groups.<group>]`` in ``pyproject.toml``.

    Idempotent: a package whose bare name is already present is skipped. The group
    is created when absent. Non-string entries (e.g. ``{include-group = ...}``) are
    preserved and ignored for duplicate detection.

    When *dry_run* is ``True``, returns packages that would be added without writing.
    """
    data = _load(project_root)
    groups: dict[str, list[object]] = data.setdefault("dependency-groups", {})
    entries: list[object] = groups.setdefault(group, [])
    existing = [e for e in entries if isinstance(e, str)]
    to_add = _missing(existing, packages)
    if not to_add:
        return []

    if not dry_run:
        entries.extend(to_add)
        _save(project_root, data, dry_run=False)

    return to_add


def update_project_scripts(
    project_root: Path,
    pkg: ProjectContext,
    entry_fn: str = "start_server",
    *,
    dry_run: bool = False,
) -> bool:
    """Rewrite ``[project.scripts]`` so the CLI entry calls *entry_fn*.

    Sets ``<pkg> = "<pkg>.server:<entry_fn>"`` in ``pyproject.toml``.
    Idempotent: returns ``False`` immediately when the entry already has the
    correct value, leaving the file unchanged.

    When *dry_run* is ``True``, returns whether a write would occur without modifying the file.
    """
    data = _load(project_root)
    new_value = f"{pkg.python_package}.server:{entry_fn}"
    scripts: dict[str, str] = data.setdefault("project", {}).setdefault("scripts", {})
    if scripts.get(pkg.python_package_script) == new_value:
        return False

    if not dry_run:
        scripts[pkg.python_package_script] = new_value
        _save(project_root, data, dry_run=False)
    return True
