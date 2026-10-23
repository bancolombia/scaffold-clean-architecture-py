"""delete_module: safely remove a previously generated module and its test mirror (T039)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import console, require_project_root, validate_name_or_exit
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.module_locator import find_module_targets
from scaffold_ca_python.core.name_utils import to_snake_case, validate_module_name
from scaffold_ca_python.core.project_detector import load_project_context
from scaffold_ca_python.factory.simple.delete_module_factory import DeleteModuleFactory
from scaffold_ca_python.models.context import ModuleContext
from scaffold_ca_python.models.layer import Layer

_DM_HELP = "Delete a previously generated module and its test mirror. Alias 'dm'."
_DM_EPILOG = "Examples:\n\n  * scaffold dm --name order\n\n  * scaffold delete-module --name my_adapter\n\n"


def _display(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _delete_module_impl(name: str, confirm: bool, dry_run: bool) -> None:
    validate_name_or_exit(name, validate_module_name)
    project_root = require_project_root()
    project_ctx = load_project_context(project_root)

    # Create a placeholder ModuleContext for the factory (layer doesn't matter for delete)
    module_ctx = ModuleContext(name=name, layer=Layer.HELPERS, project=project_ctx)

    # Find targets
    snake = to_snake_case(name)
    targets = find_module_targets(project_root, project_ctx.python_package, snake)

    if not targets:
        console.print(
            f"[red]Error:[/red] No module named '{snake}' found in project.\n"
            "[dim]Hint:[/dim] Check spelling with 'scaffold vs' to list modules."
        )
        raise typer.Exit(code=1) from None

    # dry_run OR no --confirm → preview mode only
    if dry_run or not confirm:
        console.print("The following files would be deleted:\n")
        for src_path, test_path in targets:
            console.print(f"  {_display(src_path, project_root)}")
            if test_path:
                console.print(f"  {_display(test_path, project_root)}")
        console.print("\nRun with --confirm to proceed.")
        return

    # Use factory for deletion (only when confirm=True and not dry_run)
    builder = ModuleBuilder(
        project_root=project_root,
        project_ctx=project_ctx,
        module_ctx=module_ctx,
        dry_run=False,
    )

    DeleteModuleFactory().build(builder)

    # Persist deletion
    builder.persist()
    console.print(f"[green]✓[/green] Deleted module(s) for [bold]{name}[/bold].")


def register(app: typer.Typer) -> None:
    """Register dm / delete-module command onto *app*."""

    @app.command(
        "delete-module",
        help=_DM_HELP,
        epilog=_DM_EPILOG,
    )
    @app.command("dm", hidden=True, help=_DM_HELP, epilog=_DM_EPILOG)
    def delete_module(
        ctx: typer.Context,
        name: Annotated[
            str | None, typer.Option("--name", help="Module name (snake_case).", rich_help_panel="Required")
        ] = None,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm/--no-confirm",
                help="Skip confirmation dialog and delete immediately.",
                rich_help_panel="Options",
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run/--no-dry-run",
                help="Preview deletion without removing files.",
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
    ) -> None:
        """Delete a module and its test mirror."""
        if name is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        _delete_module_impl(name, confirm, dry_run)
