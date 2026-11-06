"""Validation rules for entry-point creation: flag compatibility and conflict detection."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.commands._shared import fail
from scaffold_ca_python.factory.entry_points.base import EntryPointFactory, EntryPointFlag


def check_flags(
    type_key: str,
    factory: type[EntryPointFactory],
    active_flags: list[EntryPointFlag],
    registry: dict[str, type[EntryPointFactory]],
) -> None:
    """Exit with an error if any active flag is not supported by the factory."""
    for flag in active_flags:
        if flag not in factory.supported_flags:
            types_supporting = [k for k, f in registry.items() if flag in f.supported_flags]
            if len(types_supporting) == 1:
                msg = f"{flag.label} {flag.verb} only valid with --type {types_supporting[0]}."
            else:
                msg = f"{flag.label} {flag.verb} not valid with --type {type_key}."
            fail(msg)


def check_conflicts(
    project_root: Path,
    src_pkg_root: Path,
    type_key: str,
    factory: type[EntryPointFactory],
    registry: dict[str, type[EntryPointFactory]],
) -> None:
    """Exit with an error if any conflicting entry-point directory already exists."""
    pkg_ep = src_pkg_root / "infrastructure" / "entry_points"
    for conflict in factory.conflicts:
        other = registry.get(conflict.type_key)
        if other is None:
            continue
        conflict_subdir = other.subdir.split("/")[0]
        conflict_dir = pkg_ep / conflict_subdir
        if conflict_dir.exists():
            rel = conflict_dir.relative_to(project_root)
            fail(
                f"Incompatible entry point '[bold]{conflict.type_key}[/bold]' already exists at: {rel}",
                hint=f"A project may have only one entry-point type. Remove '{rel}' before adding {type_key}.",
            )
