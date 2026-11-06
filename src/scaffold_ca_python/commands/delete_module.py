"""delete_module: safely remove a previously generated module and its test mirror."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import (
    DryRunDelete,
    console,
    fail,
    register_with_alias,
    require_wireup_context,
    show_help_if_missing,
    validate_name_or_exit,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.module_locator import find_module_targets
from scaffold_ca_python.core.name_utils import to_snake_case, validate_module_name
from scaffold_ca_python.factory.simple.delete_module_factory import DeleteModuleFactory
from scaffold_ca_python.models.context import ModuleContext

_DM_HELP = "Delete a previously generated module and its test mirror. Alias 'dm'."
_DM_EPILOG = "Examples:\n\n  * scaffold dm --name order\n\n  * scaffold delete-module --name my_adapter\n\n"


def _display(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _delete_module_impl(name: str, confirm: bool, dry_run: bool) -> None:
    validate_name_or_exit(name, validate_module_name)
    project_root, project_ctx = require_wireup_context()

    module_ctx = ModuleContext(name=name, project=project_ctx)

    # Find targets
    snake = to_snake_case(name)
    targets = find_module_targets(project_root, project_ctx.src_pkg_root, snake)

    if not targets:
        fail(
            f"No module named '{snake}' found in project.",
            hint="Module names match directories under domain/model/ (snake_case).",
        )

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
    def delete_module(
        ctx: typer.Context,
        name: Annotated[
            str | None, typer.Option("--name", help="Module name (snake_case).", rich_help_panel="Required")
        ] = None,
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm/--no-confirm",
                help="Delete the module and its tests immediately without showing a preview.",
                rich_help_panel="Options",
            ),
        ] = False,
        dry_run: DryRunDelete = False,
    ) -> None:
        name = show_help_if_missing(ctx, name)
        _delete_module_impl(name, confirm, dry_run)

    register_with_alias(app, "delete-module", "dm", delete_module, help=_DM_HELP, epilog=_DM_EPILOG)
