"""generate_helper: scaffold a helper utility class and test stub."""

from __future__ import annotations

from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import (
    build_and_persist,
    console,
    ensure_absent,
    print_dry_run_tree,
    require_project_root,
    validate_name_or_exit,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import to_snake_case, validate_module_name
from scaffold_ca_python.core.project_detector import load_project_context
from scaffold_ca_python.factory.simple.helper_factory import HelperFactory
from scaffold_ca_python.models.context import ModuleContext
from scaffold_ca_python.models.layer import Layer

_GH_HELP = "Scaffold a helper utility module and test stub. Alias 'gh'."
_GH_EPILOG = "Example:\n\n  * scaffold gh --name json_parser\n\n  * scaffold generate-helper --name json_parser\n\n"


def _generate_helper_impl(name: str, dry_run: bool) -> None:
    validate_name_or_exit(name, validate_module_name)
    project_root = require_project_root()
    project_ctx = load_project_context(project_root)
    module_ctx = ModuleContext(name=name, layer=Layer.HELPERS, project=project_ctx)

    snake = to_snake_case(name)
    src_dir = project_root / "src" / project_ctx.python_package / "infrastructure" / "helpers" / snake
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
    """Register gh / generate-helper commands onto *app*."""

    @app.command("generate-helper", help=_GH_HELP, epilog=_GH_EPILOG)
    @app.command("gh", hidden=True, help=_GH_HELP, epilog=_GH_EPILOG)
    def generate_helper(
        ctx: typer.Context,
        name: Annotated[
            str | None, typer.Option("--name", help="Helper name (snake_case).", rich_help_panel="Required")
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run/--no-dry-run",
                help="Preview without writing.",
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
    ) -> None:
        """Scaffold a helper in infrastructure/helpers/."""
        if name is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        _generate_helper_impl(name, dry_run)
