"""generate_pipeline: scaffold a CI/CD pipeline configuration file."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.tree import Tree

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import ScaffoldError
from scaffold_ca_python.core.project_detector import find_project_root
from scaffold_ca_python.factory.pipelines import PIPELINE_PROVIDERS
from scaffold_ca_python.models.context import ProjectContext

if TYPE_CHECKING:
    from scaffold_ca_python.core.file_writer import FileWriter
    from scaffold_ca_python.core.template_renderer import TemplateRenderer

console = Console()

_GPIPE_HELP = "Scaffold a CI/CD pipeline configuration file. Alias: 'gpipe'"
_GPIPE_EPILOG = (
    "Providers:\n\n"
    "  * github    GitHub Actions (.github/workflows/ci.yml)\n\n"
    "  * azure     Azure Pipelines (azure-pipelines.yml)\n\n"
    " ==================================================\n\n"
    "Note: --provider is required.\n\n"
    "Examples:\n\n"
    "  * scaffold gpipe --provider github\n\n"
    "  * scaffold generate-pipeline --provider azure"
)


def _generate_pipeline_impl(
    provider: str | None,
    dry_run: bool,
    *,
    renderer: TemplateRenderer | None = None,
    writer: FileWriter | None = None,
) -> None:
    allowed = ", ".join(PIPELINE_PROVIDERS.keys())

    # --- Validate provider presence ---
    if not provider:
        console.print(f"[red]Error:[/red] --provider is required. Choose from: {allowed}.")
        raise typer.Exit(code=1) from None

    # --- Validate provider value ---
    if provider not in PIPELINE_PROVIDERS:
        console.print(f"[red]Error:[/red] Unknown provider '{provider}'. Allowed: {allowed}.")
        raise typer.Exit(code=1) from None

    pipeline = PIPELINE_PROVIDERS[provider]

    # --- Locate project root ---
    try:
        project_root = find_project_root()
    except ScaffoldError:
        console.print("[red]Error:[/red] No scaffold-ca-python project found. Run 'scaffold ca' first.")
        raise typer.Exit(code=1) from None

    project_ctx = _load_project_context(project_root)
    out_path = project_root / pipeline.output_path

    # --- Duplicate guard ---
    if out_path.exists():
        console.print(
            f"[red]Error:[/red] '{pipeline.display_name}' already exists at "
            f"'{out_path.relative_to(project_root)}'. Use --force to overwrite.\n"
            "[dim]Hint:[/dim] Remove the existing file first or choose a different provider."
        )
        raise typer.Exit(code=1) from None

    builder = ModuleBuilder(
        project_root=project_root,
        project_ctx=project_ctx,
        dry_run=dry_run,
        file_writer=writer,
        template_renderer=renderer,
    )

    pipeline.build(builder)
    created = builder.persist()

    if dry_run:
        tree = Tree(f"[bold]{pipeline.display_name}[/bold] (dry run)")
        for p in sorted(created):
            tree.add(str(p.relative_to(project_root)))
        console.print(tree)
        return

    console.print(
        f"[green]✓[/green] Pipeline [bold]{pipeline.display_name}[/bold] created. Created {len(created)} file(s)."
    )


def register(app: typer.Typer) -> None:
    """Register gpipe / generate-pipeline commands onto *app*."""

    @app.command(
        "generate-pipeline",
        help=_GPIPE_HELP,
        epilog=_GPIPE_EPILOG,
    )
    @app.command("gpipe", hidden=True, help=_GPIPE_HELP, epilog=_GPIPE_EPILOG)
    def generate_pipeline(
        ctx: typer.Context,
        provider: Annotated[
            str | None,
            typer.Option(
                "--provider",
                help="Pipeline provider (github, azure).",
                rich_help_panel="Required",
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
        """Scaffold a CI/CD pipeline file for the specified provider."""
        if provider is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        _generate_pipeline_impl(provider, dry_run)


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
