"""Shared utilities for CLI commands."""

from __future__ import annotations

import subprocess
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
    from scaffold_ca_python.models.context import ProjectContext

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


def auto_format_project(project_root: Path) -> None:
    """Run ruff check --fix (I rules) then ruff format on *project_root* (best-effort).

    Silently skips when ruff is not on PATH.
    """
    for cmd in (
        ["ruff", "check", "--fix", "--select", "I", "--quiet", "--no-cache", "."],
        ["ruff", "format", "--quiet", "--no-cache", "."],
    ):
        try:
            subprocess.run(cmd, cwd=project_root, check=False, capture_output=True)
        except FileNotFoundError:
            return


def build_and_persist(factory: ModuleFactory, builder: ModuleBuilder) -> list[Path]:
    """Build and persist module operations, returning the affected paths."""
    factory.build(builder)
    paths = builder.persist()
    if not builder.dry_run:
        auto_format_project(builder.project_root)
    return paths


def warn_legacy_project(ctx: ProjectContext) -> None:
    """Print a Rich-formatted warning for legacy projects (scaffold_version absent)."""
    console.print(
        f"[yellow]⚠ Warning:[/yellow] Project [bold]{ctx.name}[/bold] uses the legacy "
        "[bold]dependency-injector[/bold] DI framework.\n"
        "[dim]Run [bold]scaffold migrate-di[/bold] to migrate to wireup and remove this warning.[/dim]"
    )


def require_wireup_project(ctx: ProjectContext) -> None:
    """Exit with code 1 when *ctx* is a legacy project (scaffold_version absent)."""
    if ctx.is_legacy:
        console.print(
            f"[red]✗ Error:[/red] Project [bold]{ctx.name}[/bold] was generated with "
            "scaffold-ca-python ≤ 0.5.0 (dependency-injector).\n"
            "[dim]Migrate it first:\n"
            "  [bold]scaffold migrate-di[/bold]          – automated codemod\n"
            "  [bold]scaffold migrate-di --install-skill[/bold]  – AI-guided migration[/dim]"
        )
        raise SystemExit(1)


def find_gateway(project_root: Path, pkg: str, gateway_name: str) -> str | None:
    """Walk domain/model/*/gateways/ and return the model directory name if the gateway file is found."""
    gateways_base = project_root / "src" / pkg / "domain" / "model"
    if not gateways_base.is_dir():
        return None
    for model_dir in gateways_base.iterdir():
        if not model_dir.is_dir():
            continue
        gateway_file = model_dir / "gateways" / f"{gateway_name}.py"
        if gateway_file.exists():
            return model_dir.name
    return None


def dry_run_option(help: str = "Preview without writing.") -> typer.models.OptionInfo:
    """Return a ``--dry-run/--no-dry-run`` Typer option."""
    return typer.models.OptionInfo(
        default=False,
        param_decls=("--dry-run/--no-dry-run",),
        help=help,
        rich_help_panel="Options",
        show_default=True,
    )
