"""generate_use_case: scaffold an async use case class and test stub."""

from __future__ import annotations

from pathlib import Path
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
    register_with_alias,
    require_wireup_context,
    show_help_if_missing,
    validate_name_or_exit,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import strip_usecase_suffix, to_snake_case, validate_module_name
from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.core.wiring_utils import find_missing_adapters, sync_wiring_marker
from scaffold_ca_python.factory.simple.use_case_factory import UseCaseFactory, _gateway_context
from scaffold_ca_python.models.context import ModuleContext, ProjectContext

_GUC_HELP = "Scaffold a use case in domain/usecase/. Alias 'guc'."
_GUC_EPILOG = (
    "Example:\n\n"
    "  * scaffold guc --name create_order   (creates domain/usecase/create_order_usecase.py)\n\n"
    "  * scaffold guc --name create_order --uses order_repository   (also creates DI factory)\n\n"
    "  * scaffold generate-use-case --name create_order\n\n"
)


def _is_helper_or_adapter(pkg_root: Path, name: str) -> bool:
    """Return True if name matches a helper or driven-adapter directory/file."""
    infra = pkg_root / "infrastructure"
    for subdir in ("helpers", "driven_adapters"):
        candidate = infra / subdir / name
        if candidate.is_dir() or (infra / subdir / f"{name}.py").exists():
            return True
    return False


def _validate_gateways(project_root: Path, project_ctx: ProjectContext, uses: str) -> list[dict[str, str]]:
    """Parse and validate the --uses value; return list of gateway context dicts."""
    gateway_names = [g.strip() for g in uses.split(",") if g.strip()]
    result = []
    for gw_name in gateway_names:
        if _is_helper_or_adapter(project_ctx.src_pkg_root, gw_name):
            fail(
                f"'{gw_name}' is an infrastructure module (helper or adapter), not a gateway.",
                hint=(
                    "Helpers and adapters are infrastructure-only. "
                    "Use cases may only depend on domain gateways. "
                    "Define an ABC gateway in domain/model/<model>/gateways/ instead."
                ),
            )
        model_module = find_gateway(project_ctx.src_pkg_root, gw_name)
        if model_module is None:
            fail(
                f"Gateway '{gw_name}' not found in domain/model/*/gateways/.",
                hint=(
                    f"Run 'scaffold gm --name <model>' to create a model with a gateway, "
                    f"then retry with --uses {gw_name}."
                ),
            )
        result.append(_gateway_context(gw_name, model_module))
    return result


def _generate_use_case_impl(name: str, dry_run: bool, uses: str | None) -> None:
    validate_name_or_exit(name, validate_module_name)
    base = strip_usecase_suffix(to_snake_case(name))
    if not base:
        fail(
            f"Use case name '{name}' is only the 'usecase' suffix.",
            hint="Use a descriptive name such as 'create_order'.",
        )
    project_root, project_ctx = require_wireup_context()
    module_ctx = ModuleContext(name=base, project=project_ctx)

    module = f"{base}_usecase"
    src_path = project_ctx.src_pkg_root / "domain" / "usecase" / f"{module}.py"
    test_path = resolve_tests_root(project_root) / "domain" / "usecase" / f"test_{module}.py"
    for path in (src_path, test_path):
        ensure_absent(
            path,
            project_root,
            kind="File",
            hint="Choose a different name or remove the existing file first.",
        )

    gateways = _validate_gateways(project_root, project_ctx, uses) if uses else []

    builder = ModuleBuilder(project_root=project_root, project_ctx=project_ctx, module_ctx=module_ctx, dry_run=dry_run)
    if gateways:
        builder.add_param("gateways", gateways)

    created = build_and_persist(UseCaseFactory(), builder)

    if dry_run:
        print_dry_run_tree(module, created, project_root)
        return

    msg = (
        f"[green]✓[/green] Use case [bold]{module_ctx.class_name}UseCase[/bold] "
        f"created. Created {len(created)} file(s)."
    )
    console.print(msg)

    # Hint when no adapter implements the gateway yet
    if gateways:
        tests_root = resolve_tests_root(project_root)
        sync_wiring_marker(project_ctx.src_pkg_root, tests_root)
        _warn_missing_adapters(project_ctx.src_pkg_root, gateways)


def _warn_missing_adapters(src_pkg_root: Path, gateways: list[dict[str, str]]) -> None:
    """Print a hint for each gateway that has no wireup adapter yet."""
    missing = set(find_missing_adapters(src_pkg_root))
    for gw in gateways:
        if gw["class_name"] in missing:
            console.print(
                f"[yellow]⚠[/yellow]  No adapter implements [bold]{gw['class_name']}[/bold] yet.\n"
                f"   Run: [dim]scaffold gda --type generic "
                f"--name {gw['name']}_adapter --gateway {gw['name']}[/dim]"
            )


def register(app: typer.Typer) -> None:
    def generate_use_case(
        ctx: typer.Context,
        name: Annotated[
            str | None, typer.Option("--name", help="Use case name (snake_case).", rich_help_panel="Required")
        ] = None,
        uses: Annotated[
            str | None,
            typer.Option(
                "--uses",
                help="Comma-separated domain gateway names to inject (e.g. order_repository). Gateways only.",
                rich_help_panel="Options",
            ),
        ] = None,
        dry_run: DryRun = False,
    ) -> None:
        name = show_help_if_missing(ctx, name)
        _generate_use_case_impl(name, dry_run, uses)

    register_with_alias(app, "generate-use-case", "guc", generate_use_case, help=_GUC_HELP, epilog=_GUC_EPILOG)
