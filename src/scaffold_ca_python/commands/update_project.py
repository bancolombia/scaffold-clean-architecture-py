"""update_project: upgrade dependencies via uv."""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from scaffold_ca_python.commands._shared import (
    DryRunUpdate,
    console,
    fail,
    register_with_alias,
    require_project_root,
)

_GUP = "Update project dependencies via uv lock --upgrade + uv sync. Alias: 'up'"
_GUP_EPILOG = "Example:\n\n  * scaffold up --dry-run\n\n  * scaffold update-project --dry-run"


def _run_uv(cmd: list[str], cwd: Path, failure_message: str) -> None:
    """Run a uv command, exiting 1 if uv is missing or 2 on a non-zero return code."""
    try:
        subprocess.run(cmd, check=True, cwd=cwd)
    except FileNotFoundError:
        fail("'uv' is not installed or not on PATH. Install it from https://docs.astral.sh/uv/")
    except subprocess.CalledProcessError:
        fail(failure_message, code=2)


def _update_project_impl(dry_run: bool) -> None:
    # Intentionally uses require_project_root (not require_wireup_context): uv commands
    # work on both legacy and wireup projects.
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
    def update_project(
        dry_run: DryRunUpdate = False,
    ) -> None:
        _update_project_impl(dry_run)

    register_with_alias(app, "update-project", "up", update_project, help=_GUP, epilog=_GUP_EPILOG)
