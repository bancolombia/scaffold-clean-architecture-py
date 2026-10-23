"""generate_driven_adapter: scaffold a driven adapter and test stub."""

from __future__ import annotations

from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import (
    build_and_persist,
    console,
    ensure_absent,
    fail,
    print_dry_run_tree,
    print_pending_dependencies,
    require_project_root,
    validate_name_or_exit,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import to_snake_case, validate_module_name
from scaffold_ca_python.core.project_detector import load_project_context
from scaffold_ca_python.factory.driven_adapters import DRIVEN_ADAPTER_FACTORIES
from scaffold_ca_python.models.context import ModuleContext
from scaffold_ca_python.models.layer import Layer

_GDA_HELP = "Scaffold a driven adapter and test stub. Alias 'gda'."
_GDA_EPILOG = (
    "Types:\n\n"
    "  * rest-consumer    HTTP outbound client (httpx)\n\n"
    "  * secrets          AWS Secrets Manager (boto3)\n\n"
    "  * generic          Custom adapter (--name required)\n\n"
    " ==================================================\n\n"
    "Examples:\n\n"
    "  * scaffold gda --type rest-consumer\n\n"
    "  * scaffold generate-driven-adapter --type generic --name my_adapter\n\n"
)


def _generate_driven_adapter_impl(type_: str, name: str | None, dry_run: bool) -> None:
    if type_ not in DRIVEN_ADAPTER_FACTORIES:
        allowed = ", ".join(DRIVEN_ADAPTER_FACTORIES.keys())
        fail(f"Unknown type '{type_}'. Allowed: {allowed}.")

    factory_class = DRIVEN_ADAPTER_FACTORIES[type_]
    factory = factory_class()
    mod_name = factory.module_name(name)

    if mod_name is None:
        fail(f"--name is required when --type is {type_}.")

    if name:
        validate_name_or_exit(name, validate_module_name)

    project_root = require_project_root()
    project_ctx = load_project_context(project_root)
    subdir = to_snake_case(mod_name)
    module_ctx = ModuleContext(name=mod_name, layer=Layer.DRIVEN_ADAPTERS, project=project_ctx)

    src_dir = project_root / "src" / project_ctx.python_package / "infrastructure" / "driven_adapters" / subdir
    ensure_absent(
        src_dir,
        project_root,
        kind="Directory",
        hint="Choose a different name or remove the existing directory first.",
    )

    builder = ModuleBuilder(
        project_root=project_root,
        project_ctx=project_ctx,
        module_ctx=module_ctx,
        dry_run=dry_run,
    )
    created = build_and_persist(factory, builder)

    if dry_run:
        print_dry_run_tree(subdir, created, project_root)
        print_pending_dependencies(builder)
        return

    console.print(f"[green]✓[/green] Driven adapter [bold]{subdir}[/bold] created. Created {len(created)} file(s).")


def register(app: typer.Typer) -> None:
    """Register gda / generate-driven-adapter commands onto *app*."""

    @app.command(
        "generate-driven-adapter",
        help=_GDA_HELP,
        epilog=_GDA_EPILOG,
    )
    @app.command("gda", hidden=True, help=_GDA_HELP, epilog=_GDA_EPILOG)
    def generate_driven_adapter(
        ctx: typer.Context,
        type_: Annotated[
            str | None,
            typer.Option(
                "--type",
                help="Adapter type: rest-consumer, secrets, generic.",
                rich_help_panel="Required",
            ),
        ] = None,
        name: Annotated[
            str | None,
            typer.Option(
                "--name",
                help="Adapter name in snake_case, e.g. my_adapter (required for --type generic).",
                rich_help_panel="Options",
            ),
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
        """Scaffold a driven adapter inside infrastructure/driven_adapters/."""
        if type_ is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        _generate_driven_adapter_impl(type_, name, dry_run)
