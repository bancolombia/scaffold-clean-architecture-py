"""generate_helper: scaffold a helper utility class and test stub."""

from __future__ import annotations

from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import (
    DryRun,
    build_and_persist,
    console,
    ensure_absent,
    print_dry_run_tree,
    register_with_alias,
    require_wireup_context,
    show_help_if_missing,
    validate_name_or_exit,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import to_snake_case, validate_module_name
from scaffold_ca_python.factory.simple.helper_factory import HelperFactory
from scaffold_ca_python.models.context import ModuleContext

_GH_HELP = "Scaffold a helper utility module and test stub. Alias 'gh'."
_GH_EPILOG = "Example:\n\n  * scaffold gh --name json_parser\n\n  * scaffold generate-helper --name json_parser\n\n"


def _generate_helper_impl(name: str, dry_run: bool) -> None:
    validate_name_or_exit(name, validate_module_name)
    project_root, project_ctx = require_wireup_context()
    module_ctx = ModuleContext(name=name, project=project_ctx)

    snake = to_snake_case(name)
    src_dir = project_ctx.src_pkg_root / "infrastructure" / "helpers" / snake
    ensure_absent(
        src_dir,
        project_root,
        kind="Directory",
        hint="Choose a different name or remove the existing directory first.",
    )

    builder = ModuleBuilder(project_root=project_root, project_ctx=project_ctx, module_ctx=module_ctx, dry_run=dry_run)
    created = build_and_persist(HelperFactory(), builder)

    if dry_run:
        print_dry_run_tree(snake, created, project_root)
        return

    msg = f"[green]✓[/green] Helper [bold]{module_ctx.class_name}[/bold] created. Created {len(created)} file(s)."
    console.print(msg)


def register(app: typer.Typer) -> None:
    def generate_helper(
        ctx: typer.Context,
        name: Annotated[
            str | None, typer.Option("--name", help="Helper name (snake_case).", rich_help_panel="Required")
        ] = None,
        dry_run: DryRun = False,
    ) -> None:
        name = show_help_if_missing(ctx, name)
        _generate_helper_impl(name, dry_run)

    register_with_alias(app, "generate-helper", "gh", generate_helper, help=_GH_HELP, epilog=_GH_EPILOG)
