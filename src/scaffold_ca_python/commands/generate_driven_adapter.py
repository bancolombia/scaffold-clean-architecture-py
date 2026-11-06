"""generate_driven_adapter: scaffold a driven adapter and test stub."""

from __future__ import annotations

from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import (
    DryRun,
    build_and_persist,
    console,
    ensure_absent,
    fail,
    find_gateway,
    print_dry_run_tree,
    print_pending_dependencies,
    register_with_alias,
    require_wireup_context,
    show_help_if_missing,
    validate_name_or_exit,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import to_pascal_case, to_snake_case, validate_module_name
from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.core.wiring_utils import sync_wiring_marker
from scaffold_ca_python.factory.driven_adapters import DRIVEN_ADAPTER_FACTORIES
from scaffold_ca_python.models.context import ModuleContext

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


def _generate_driven_adapter_impl(
    type_: str,
    name: str | None,
    dry_run: bool,
    gateway: str | None = None,
) -> None:
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

    project_root, project_ctx = require_wireup_context()
    subdir = to_snake_case(mod_name)
    module_ctx = ModuleContext(name=mod_name, project=project_ctx)

    src_dir = project_ctx.src_pkg_root / "infrastructure" / "driven_adapters" / subdir
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

    if gateway:
        model_module = find_gateway(project_ctx.src_pkg_root, gateway)
        if model_module is None:
            fail(
                f"Gateway '{gateway}' not found in domain/model/*/gateways/.",
                hint="Run 'scaffold gm --name <model>' to create a model with a gateway first.",
            )
        builder.add_param(
            "gateway",
            {
                "name": gateway,
                "class_name": to_pascal_case(gateway),
                "model_module": model_module,
            },
        )

    created = build_and_persist(factory, builder)

    if dry_run:
        print_dry_run_tree(subdir, created, project_root)
        print_pending_dependencies(builder)
        return

    if gateway:
        sync_wiring_marker(project_ctx.src_pkg_root, resolve_tests_root(project_root))

    console.print(f"[green]✓[/green] Driven adapter [bold]{subdir}[/bold] created. Created {len(created)} file(s).")


def register(app: typer.Typer) -> None:
    """Register gda / generate-driven-adapter commands onto *app*."""

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
        dry_run: DryRun = False,
        gateway: Annotated[
            str | None,
            typer.Option(
                "--gateway",
                help="Domain gateway ABC this adapter implements (e.g. book_repository).",
                rich_help_panel="Options",
            ),
        ] = None,
    ) -> None:
        """Scaffold a driven adapter inside infrastructure/driven_adapters/."""
        type_ = show_help_if_missing(ctx, type_)
        _generate_driven_adapter_impl(type_, name, dry_run, gateway)

    register_with_alias(
        app, "generate-driven-adapter", "gda", generate_driven_adapter, help=_GDA_HELP, epilog=_GDA_EPILOG
    )
