"""generate_pipeline: scaffold a CI/CD pipeline configuration file."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer

from scaffold_ca_python.commands._shared import (
    DryRun,
    console,
    print_dry_run_tree,
    register_with_alias,
    require_wireup_context,
    show_help_if_missing,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.factory.pipelines import PIPELINE_PROVIDERS

if TYPE_CHECKING:
    from scaffold_ca_python.core.file_writer import FileWriter
    from scaffold_ca_python.core.template_renderer import TemplateRenderer

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

    if not provider:
        console.print(f"[red]Error:[/red] --provider is required. Choose from: {allowed}.")
        raise typer.Exit(code=1)

    if provider not in PIPELINE_PROVIDERS:
        console.print(f"[red]Error:[/red] Unknown provider '{provider}'. Allowed: {allowed}.")
        raise typer.Exit(code=1)

    pipeline = PIPELINE_PROVIDERS[provider]
    project_root, project_ctx = require_wireup_context()
    out_path = project_root / pipeline.output_path

    if out_path.exists():
        console.print(
            f"[red]Error:[/red] '{pipeline.display_name}' already exists at "
            f"'{out_path.relative_to(project_root)}'.\n"
            "[dim]Hint:[/dim] Remove the existing file first or choose a different provider."
        )
        raise typer.Exit(code=1)

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
        print_dry_run_tree(pipeline.display_name, created, project_root)
        return

    console.print(
        f"[green]✓[/green] Pipeline [bold]{pipeline.display_name}[/bold] created. Created {len(created)} file(s)."
    )


def register(app: typer.Typer) -> None:
    """Register gpipe / generate-pipeline commands onto *app*."""

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
        dry_run: DryRun = False,
    ) -> None:
        """Scaffold a CI/CD pipeline file for the specified provider."""
        provider = show_help_if_missing(ctx, provider)
        _generate_pipeline_impl(provider, dry_run)

    register_with_alias(app, "generate-pipeline", "gpipe", generate_pipeline, help=_GPIPE_HELP, epilog=_GPIPE_EPILOG)
