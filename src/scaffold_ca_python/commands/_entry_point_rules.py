"""Validation rules for entry-point creation: flag compatibility and conflict detection."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from scaffold_ca_python.commands._shared import console
from scaffold_ca_python.factory.entry_points.base import EntryPointFactory, EntryPointFlag

if TYPE_CHECKING:
    pass


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
            console.print(f"[red]Error:[/red] {msg}")
            raise typer.Exit(code=1) from None


def check_conflicts(
    project_root: Path,
    pkg: str,
    type_key: str,
    factory: type[EntryPointFactory],
) -> None:
    """Exit with an error if any conflicting entry-point directory already exists."""
    pkg_ep = project_root / "src" / pkg / "infrastructure" / "entry_points"
    for conflict in factory.conflicts:
        conflict_dir = pkg_ep / conflict.subdir
        if conflict_dir.exists():
            rel = conflict_dir.relative_to(project_root)
            console.print(
                f"[red]Error:[/red] Incompatible entry point '[bold]{conflict.label}[/bold]' "
                f"already exists at: {rel}\n"
                "[dim]Hint:[/dim] A project may have only one entry-point type. "
                f"Remove '{rel}' before adding {type_key}."
            )
            raise typer.Exit(code=1) from None
