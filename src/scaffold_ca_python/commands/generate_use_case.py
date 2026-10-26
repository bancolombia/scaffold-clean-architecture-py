"""generate_use_case: scaffold an async use case class and test stub."""

from __future__ import annotations

from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import (
    build_and_persist,
    console,
    ensure_absent,
    fail,
    print_dry_run_tree,
    require_project_root,
    validate_name_or_exit,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import strip_usecase_suffix, to_snake_case, validate_module_name
from scaffold_ca_python.core.project_detector import load_project_context, resolve_tests_root
from scaffold_ca_python.factory.simple.use_case_factory import UseCaseFactory
from scaffold_ca_python.models.context import ModuleContext
from scaffold_ca_python.models.layer import Layer

_GUC_HELP = "Scaffold a use case in domain/usecase/. Alias 'guc'."
_GUC_EPILOG = (
    "Example:\n\n  * scaffold guc --name create_order   (creates domain/usecase/create_order_usecase.py)\n\n"
    "  * scaffold generate-use-case --name create_order\n\n"
)


def _generate_use_case_impl(name: str, dry_run: bool) -> None:
    validate_name_or_exit(name, validate_module_name)
    base = strip_usecase_suffix(to_snake_case(name))
    if not base:
        fail(
            f"Use case name '{name}' is only the 'usecase' suffix.",
            hint="Use a descriptive name such as 'create_order'.",
        )
    project_root = require_project_root()
    project_ctx = load_project_context(project_root)
    module_ctx = ModuleContext(name=base, layer=Layer.DOMAIN_USECASE, project=project_ctx)

    module = f"{base}_usecase"
    src_path = project_root / "src" / project_ctx.python_package / "domain" / "usecase" / f"{module}.py"
    test_path = resolve_tests_root(project_root) / "domain" / "usecase" / f"test_{module}.py"
    for path in (src_path, test_path):
        ensure_absent(
            path,
            project_root,
            kind="File",
            hint="Choose a different name or remove the existing file first.",
        )

    builder = ModuleBuilder(project_root=project_root, project_ctx=project_ctx, module_ctx=module_ctx, dry_run=dry_run)
    created = build_and_persist(UseCaseFactory(), builder)

    if dry_run:
        print_dry_run_tree(module, created, project_root)
        return

    msg = (
        f"[green]✓[/green] Use case [bold]{module_ctx.class_name}UseCase[/bold] "
        f"created. Created {len(created)} file(s)."
    )
    console.print(msg)


def register(app: typer.Typer) -> None:
    """Register guc / generate-use-case commands onto *app*."""

    @app.command("generate-use-case", help=_GUC_HELP, epilog=_GUC_EPILOG)
    @app.command("guc", hidden=True, help=_GUC_HELP, epilog=_GUC_EPILOG)
    def generate_use_case(
        ctx: typer.Context,
        name: Annotated[
            str | None, typer.Option("--name", help="Use case name (snake_case).", rich_help_panel="Required")
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
        """Scaffold a use case in domain/usecase/."""
        if name is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        _generate_use_case_impl(name, dry_run)
