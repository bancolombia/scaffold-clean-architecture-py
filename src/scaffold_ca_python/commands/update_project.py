"""update_project: upgrade dependencies via uv."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import console, require_project_root

_GUP = "Update project dependencies via uv lock --upgrade + uv sync. Alias: 'up'"
_GUP_EPILOG = "Example:\n\n  * scaffold up --dry-run\n\n  * scaffold update-project --dry-run"


def _run_uv(cmd: list[str], cwd: Path, failure_message: str) -> None:
    """Run a uv command, exiting 1 if uv is missing or 2 on a non-zero return code."""
    try:
        subprocess.run(cmd, check=True, cwd=cwd)
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] 'uv' is not installed or not on PATH. Install it from https://docs.astral.sh/uv/"
        )
        raise typer.Exit(code=1) from None
    except subprocess.CalledProcessError:
        console.print(f"[red]Error:[/red] {failure_message}")
        raise typer.Exit(code=2) from None


def _update_project_impl(dry_run: bool) -> None:
    project_root = require_project_root()

    lock_cmd = ["uv", "lock", "--upgrade"]
    sync_cmd = ["uv", "sync"]

    if dry_run:
        console.print("Would run:")
        console.print(f"  {' '.join(lock_cmd)}   (cwd: {project_root})")
        console.print(f"  {' '.join(sync_cmd)}             (cwd: {project_root})")
        return

    _run_uv(lock_cmd, project_root, "Dependency lock failed. See output above.")
    _run_uv(sync_cmd, project_root, "Sync failed. See output above.")

    console.print("[green]✓[/green] Locked updated dependencies.")
    console.print("[green]✓[/green] Synced virtual environment.")


def register(app: typer.Typer) -> None:
    """Register up / update-project commands onto *app*."""

    @app.command(
        "update-project",
        help=_GUP,
        epilog=_GUP_EPILOG,
    )
    @app.command("up", hidden=True, help=_GUP, epilog=_GUP_EPILOG)
    def update_project(
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run/--no-dry-run",
                help="Preview commands without running.",
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
    ) -> None:
        """Update dependencies using uv."""
        _update_project_impl(dry_run)
