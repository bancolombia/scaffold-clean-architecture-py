"""Shared utilities for CLI commands."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NoReturn

import typer
from rich.console import Console
from rich.markup import escape
from rich.tree import Tree

from scaffold_ca_python.core.name_utils import ScaffoldError
from scaffold_ca_python.core.project_detector import find_project_root

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder
    from scaffold_ca_python.factory import ModuleFactory

console = Console()

PROJECT_NOT_FOUND = "No scaffold-ca-python project found. Run 'scaffold ca' first."


def fail(message: str, hint: str | None = None) -> NoReturn:
    """Print an error (and optional hint) then exit with code 1."""
    console.print(f"[red]Error:[/red] {message}")
    if hint is not None:
        console.print(f"[dim]Hint:[/dim] {hint}")
    raise typer.Exit(code=1)


def require_project_root(not_found_message: str | None = PROJECT_NOT_FOUND) -> Path:
    """Return the project root, or exit 1 if not found.

    Args:
        not_found_message: Text to print on failure. Pass ``None`` to print the
            ``ScaffoldError`` text from ``find_project_root`` instead.
    """
    try:
        return find_project_root()
    except ScaffoldError as exc:
        if not_found_message is None:
            console.print(f"[red]Error:[/red] {exc}")
        else:
            console.print(f"[red]Error:[/red] {not_found_message}")
        raise typer.Exit(code=1) from None


def validate_name_or_exit(name: str, validator: Callable[[str], object]) -> None:
    """Run *validator* on *name*, calling ``fail()`` if it raises ``ScaffoldError``."""
    try:
        validator(name)
    except ScaffoldError as exc:
        fail(str(exc))


def ensure_absent(
    path: Path,
    project_root: Path,
    *,
    kind: Literal["File", "Directory"],
    hint: str,
) -> None:
    """Exit 1 if *path* already exists."""
    if not path.exists():
        return
    rel = path.relative_to(project_root)
    suffix = "/" if kind == "Directory" else ""
    fail(f"{kind} '{rel}{suffix}' already exists.", hint=hint)


def print_dry_run_tree(title: str, paths: Iterable[Path], base: Path) -> None:
    """Render a Rich tree of *paths* (sorted, relative to *base*) with a dry-run label."""
    tree = Tree(f"[bold]{title}[/bold] (dry run)")
    for p in sorted(paths):
        try:
            tree.add(str(p.relative_to(base)))
        except ValueError:
            tree.add(str(p))
    console.print(tree)


def print_pending_dependencies(builder: ModuleBuilder) -> None:
    """Print dry-run summaries for queued dependency injections."""
    if builder.pending_dependencies:
        target = escape("[project.dependencies]")
        console.print(f"[dim]Would add to {target}: {', '.join(builder.pending_dependencies)}[/dim]")
    for grp, pkgs in builder.pending_group_dependencies.items():
        target = escape(f"[dependency-groups.{grp}]")
        console.print(f"[dim]Would add to {target}: {', '.join(pkgs)}[/dim]")


def build_and_persist(factory: ModuleFactory, builder: ModuleBuilder) -> list[Path]:
    """Build and persist module operations, returning the affected paths."""
    factory.build(builder)
    return builder.persist()


def dry_run_option(help: str = "Preview without writing.") -> typer.models.OptionInfo:
    """Return a ``--dry-run/--no-dry-run`` Typer option."""
    return typer.models.OptionInfo(
        default=False,
        param_decls=("--dry-run/--no-dry-run",),
        help=help,
        rich_help_panel="Options",
        show_default=True,
    )
