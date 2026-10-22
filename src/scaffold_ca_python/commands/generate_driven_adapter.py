"""generate_driven_adapter: scaffold a driven adapter and test stub (T030)."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.tree import Tree

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import ScaffoldError, to_snake_case, validate_module_name
from scaffold_ca_python.core.project_detector import find_project_root
from scaffold_ca_python.factory.driven_adapters import DRIVEN_ADAPTER_FACTORIES
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from scaffold_ca_python.models.layer import Layer

console = Console()

_REGISTRY = DRIVEN_ADAPTER_FACTORIES

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
    # --- Validate type ---
    if type_ not in DRIVEN_ADAPTER_FACTORIES:
        allowed = ", ".join(DRIVEN_ADAPTER_FACTORIES.keys())
        console.print(f"[red]Error:[/red] Unknown type '{type_}'. Allowed: {allowed}.")
        raise typer.Exit(code=1) from None

    factory_class = DRIVEN_ADAPTER_FACTORIES[type_]
    factory = factory_class()
    mod_name = factory.module_name(name)

    # --- Validate name requirement ---
    if mod_name is None:
        console.print(f"[red]Error:[/red] --name is required when --type is {type_}.")
        raise typer.Exit(code=1) from None

    # --- Validate name if provided ---
    if name:
        try:
            validate_module_name(name)
        except ScaffoldError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from None

    # --- Locate project root ---
    try:
        project_root = find_project_root()
    except ScaffoldError:
        console.print("[red]Error:[/red] No scaffold-ca-python project found. Run 'scaffold ca' first.")
        raise typer.Exit(code=1) from None

    project_ctx = _load_project_context(project_root)
    subdir = to_snake_case(mod_name)
    module_ctx = ModuleContext(name=mod_name, layer=Layer.DRIVEN_ADAPTERS, project=project_ctx)

    pkg = project_ctx.python_package
    src_dir = project_root / "src" / pkg / "infrastructure" / "driven_adapters" / subdir

    # --- Duplicate guard ---
    if src_dir.exists():
        console.print(
            f"[red]Error:[/red] Directory '{src_dir.relative_to(project_root)}/' already exists.\n"
            "[dim]Hint:[/dim] Choose a different name or remove the existing directory first."
        )
        raise typer.Exit(code=1) from None

    # --- Create builder ---
    builder = ModuleBuilder(
        project_root=project_root,
        project_ctx=project_ctx,
        module_ctx=module_ctx,
        dry_run=dry_run,
    )

    factory.build(builder)
    created = builder.persist()

    # --- Display results ---
    if dry_run:
        tree = Tree(f"[bold]{subdir}[/bold] (dry run)")
        for p in sorted(created):
            tree.add(str(p.relative_to(project_root)))
        console.print(tree)
        if builder.pending_dependencies:
            target = escape("[project.dependencies]")
            console.print(f"[dim]Would add to {target}: {', '.join(builder.pending_dependencies)}[/dim]")
        for grp, pkgs in builder.pending_group_dependencies.items():
            target = escape(f"[dependency-groups.{grp}]")
            console.print(f"[dim]Would add to {target}: {', '.join(pkgs)}[/dim]")
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_project_context(root: Path) -> ProjectContext:
    pyproject = root / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    section = data.get("tool", {}).get("scaffold-ca-python", {})
    return ProjectContext(
        name=section.get("name", root.name),
    )
