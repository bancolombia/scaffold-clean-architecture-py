"""validate_structure: AST-based CA layer import checker."""

from __future__ import annotations

import typer
from rich.table import Table

from scaffold_ca_python.commands._shared import (
    DryRunValidate,
    console,
    fail,
    register_with_alias,
    require_project_root,
)
from scaffold_ca_python.core.errors import ScaffoldError
from scaffold_ca_python.core.structure_validator import StructureValidator

_validator = StructureValidator()

_GVS_HELP = "Scan src/ for Clean Architecture import violations. Alias: 'vs'."
_GVS_EPILOG = "Example:\n\n  * scaffold vs\n\n  * scaffold validate-structure\n"


def _validate_structure_impl(dry_run: bool) -> None:
    # Intentionally uses require_project_root (not require_wireup_context): structure
    # validation applies to both legacy and wireup projects.
    project_root = require_project_root()

    try:
        report = _validator.validate(project_root)
    except ScaffoldError as exc:
        fail(str(exc))

    if report.passed:
        console.print(f"[green]✓[/green] Validated [bold]{report.files_scanned}[/bold] file(s) — no violations found.")
        return

    table = Table(
        title=f"[red]✗[/red] {len(report.violations)} violation(s) found",
        show_header=True,
        header_style="bold",
    )
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Line", style="yellow", justify="right")
    table.add_column("Import", style="white", no_wrap=False)
    table.add_column("Hint", style="dim", no_wrap=False)

    for v in report.violations:
        try:
            file_str = str(v.source_file.relative_to(project_root))
        except ValueError:
            file_str = str(v.source_file)

        table.add_row(
            file_str,
            str(v.line_number),
            v.import_statement,
            v.resolution_hint,
        )

    console.print(table)

    if not dry_run:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    def validate_structure(
        dry_run: DryRunValidate = False,
    ) -> None:
        _validate_structure_impl(dry_run)

    register_with_alias(app, "validate-structure", "vs", validate_structure, help=_GVS_HELP, epilog=_GVS_EPILOG)
