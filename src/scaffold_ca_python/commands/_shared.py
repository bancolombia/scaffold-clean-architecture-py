"""Shared utilities for CLI commands."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, NoReturn, cast, overload

import typer
from rich.console import Console
from rich.markup import escape
from rich.tree import Tree

from scaffold_ca_python.core.errors import ScaffoldError
from scaffold_ca_python.core.project_detector import find_project_root, load_project_context

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder
    from scaffold_ca_python.factory import ModuleFactory
    from scaffold_ca_python.models.context import ProjectContext

console = Console()

PROJECT_NOT_FOUND = "No scaffold-ca-python project found. Run 'scaffold ca' first."


def fail(message: str, hint: str | None = None, *, code: int = 1) -> NoReturn:
    """Print an error (and optional hint) then exit."""
    console.print(f"[red]Error:[/red] {message}")
    if hint is not None:
        console.print(f"[dim]Hint:[/dim] {hint}")
    raise typer.Exit(code=code) from None


def dry_run_option(help: str = "Preview without writing.") -> typer.models.OptionInfo:
    """Return a ``--dry-run/--no-dry-run`` Typer option."""
    return cast(
        typer.models.OptionInfo,
        typer.Option("--dry-run/--no-dry-run", help=help, rich_help_panel="Options", show_default=True),
    )


DryRun = Annotated[bool, dry_run_option("Preview without writing.")]
DryRunDelete = Annotated[bool, dry_run_option("Preview deletion without removing files.")]
DryRunProject = Annotated[bool, dry_run_option("Preview files without writing.")]
DryRunValidate = Annotated[bool, dry_run_option("Print results but always exit 0.")]
DryRunUpdate = Annotated[bool, dry_run_option("Preview commands without running.")]


def require_project_root(not_found_message: str | None = PROJECT_NOT_FOUND) -> Path:
    """Return the project root, or exit 1 if not found.

    Args:
        not_found_message: Text to print on failure. Pass ``None`` to print the
            ``ScaffoldError`` text from ``find_project_root`` instead.
    """
    try:
        return find_project_root()
    except ScaffoldError as exc:
        fail(not_found_message or str(exc))


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
        console.print(f"[dim]Would add to {target}: {escape(', '.join(builder.pending_dependencies))}[/dim]")
    for grp, pkgs in builder.pending_group_dependencies.items():
        target = escape(f"[dependency-groups.{grp}]")
        console.print(f"[dim]Would add to {target}: {escape(', '.join(pkgs))}[/dim]")


def auto_format_project(project_root: Path) -> None:
    """Run ruff check --fix (I rules) then ruff format on *project_root* (best-effort).

    Silently skips when ruff is not importable in the active interpreter.
    """
    import sys

    ruff = [sys.executable, "-m", "ruff"]
    for cmd in (
        [*ruff, "check", "--fix", "--select", "I", "--quiet", "--no-cache", "."],
        [*ruff, "format", "--quiet", "--no-cache", "."],
        [*ruff, "check", "--fix", "--select", "I", "--quiet", "--no-cache", "."],
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


_LEGACY_MIGRATION_HINT = (
    "Run [bold]scaffold up[/bold] to migrate from dependency-injector to wireup "
    "(or install the agent skill with [bold]scaffold install-skill migrate-di[/bold])."
)


def require_wireup_context(
    project_root: Path | None = None,
    *,
    not_found_message: str | None = PROJECT_NOT_FOUND,
) -> tuple[Path, ProjectContext]:
    """Resolve project root, load context, and exit if the project is legacy."""
    root = project_root or require_project_root(not_found_message)
    ctx = load_project_context(root)
    require_wireup_project(ctx)
    return root, ctx


@overload
def show_help_if_missing(ctx: typer.Context, value: str) -> str: ...


@overload
def show_help_if_missing(ctx: typer.Context, value: None) -> NoReturn: ...


def show_help_if_missing(ctx: typer.Context, value: str | None) -> str:
    """Show help and exit when a required argument is missing."""
    if value is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    return value


def register_with_alias(
    app: typer.Typer,
    name: str,
    alias: str,
    fn: Callable[..., None],
    *,
    help: str,
    epilog: str,
) -> None:
    """Register a command and its hidden alias."""
    app.command(name, help=help, epilog=epilog)(fn)
    app.command(alias, hidden=True, help=help, epilog=epilog)(fn)


def require_wireup_project(ctx: ProjectContext) -> None:
    """Exit with code 1 when *ctx* is a legacy project (scaffold_version absent)."""
    if ctx.is_legacy:
        fail(
            f"Project [bold]{ctx.name}[/bold] was generated with scaffold-ca-python ≤ 0.5.0 (dependency-injector).\n"
            "[dim]This scaffolder only modifies wireup projects (1.0.0+). "
            f"{_LEGACY_MIGRATION_HINT}[/dim]"
        )


def find_gateway(src_pkg_root: Path, gateway_name: str) -> str | None:
    """Walk domain/model/*/gateways/ and return the model directory name if the gateway file is found."""
    gateways_base = src_pkg_root / "domain" / "model"
    if not gateways_base.is_dir():
        return None
    for model_dir in gateways_base.iterdir():
        if not model_dir.is_dir():
            continue
        gateway_file = model_dir / "gateways" / f"{gateway_name}.py"
        if gateway_file.exists():
            return model_dir.name
    return None
