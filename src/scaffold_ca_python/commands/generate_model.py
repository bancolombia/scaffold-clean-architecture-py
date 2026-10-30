"""generate_model: scaffold a domain model class and test stub."""

from __future__ import annotations

from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import (
    build_and_persist,
    console,
    ensure_absent,
    print_dry_run_tree,
    require_project_root,
    require_wireup_project,
    validate_name_or_exit,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import validate_module_name
from scaffold_ca_python.core.project_detector import load_project_context, resolve_tests_root
from scaffold_ca_python.factory.simple.model_factory import ModelFactory
from scaffold_ca_python.models.context import ModuleContext
from scaffold_ca_python.models.layer import Layer

_GM_HELP = "Scaffold a Pydantic v2 domain model, its gateway, and test stubs. Alias 'gm'."
_GM_EPILOG = "Example:\n\n  * scaffold gm --name order\n\n  * scaffold generate-model --name order\n\n"


def _generate_model_impl(name: str, dry_run: bool) -> None:
    validate_name_or_exit(name, validate_module_name)
    project_root = require_project_root()
    project_ctx = load_project_context(project_root)
    require_wireup_project(project_ctx)
    module_ctx = ModuleContext(name=name, layer=Layer.DOMAIN_MODEL, project=project_ctx)

    model_root = project_root / "src" / project_ctx.python_package / "domain" / "model"
    ensure_absent(
        model_root / module_ctx.module_name,
        project_root,
        kind="Directory",
        hint="Choose a different name or remove the existing folder first.",
    )
    ensure_absent(
        model_root / f"{module_ctx.module_name}.py",
        project_root,
        kind="File",
        hint="A model with this name already exists in the legacy flat layout. Remove it or choose a different name.",
    )
    ensure_absent(
        resolve_tests_root(project_root) / "domain" / "model" / module_ctx.module_name,
        project_root,
        kind="Directory",
        hint="Remove the leftover tests folder or choose a different name.",
    )

    builder = ModuleBuilder(project_root=project_root, project_ctx=project_ctx, module_ctx=module_ctx, dry_run=dry_run)
    created = build_and_persist(ModelFactory(), builder)

    if dry_run:
        print_dry_run_tree(module_ctx.module_name, created, project_root)
        return

    msg = f"[green]✓[/green] Model [bold]{module_ctx.class_name}[/bold] created. Created {len(created)} file(s)."
    console.print(msg)


def register(app: typer.Typer) -> None:
    """Register gm / generate-model commands onto *app*."""

    @app.command("generate-model", help=_GM_HELP, epilog=_GM_EPILOG)
    @app.command("gm", hidden=True, help=_GM_HELP, epilog=_GM_EPILOG)
    def generate_model(
        ctx: typer.Context,
        name: Annotated[
            str | None, typer.Option("--name", help="Model name (snake_case).", rich_help_panel="Required")
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
        """Scaffold a domain model package with its gateway in domain/model/<name>/."""
        if name is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        _generate_model_impl(name, dry_run)
