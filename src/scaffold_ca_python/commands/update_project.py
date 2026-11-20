"""update_project: upgrades + dependency refresh via uv."""

from __future__ import annotations

import json
import subprocess
import sys
from enum import StrEnum
from pathlib import Path

import typer

from scaffold_ca_python.commands._shared import (
    DryRunUpdate,
    console,
    fail,
    register_with_alias,
    require_project_root,
)
from scaffold_ca_python.factory.upgrades.report import UpgradeReport
from scaffold_ca_python.factory.upgrades.runner import UpgradeRunner

_GUP = "Run upgrade actions, then refresh dependencies via uv lock --upgrade + uv sync. Alias: 'up'"
_GUP_EPILOG = (
    "Example:\n\n  * scaffold up --dry-run\n\n  * scaffold up --report json\n\n"
    "  * scaffold update-project --skip-upgrades"
)


class ReportFormat(StrEnum):
    text = "text"
    json = "json"


def _run_uv(cmd: list[str], cwd: Path, failure_message: str) -> None:
    try:
        subprocess.run(cmd, check=True, cwd=cwd)
    except FileNotFoundError:
        fail("'uv' is not installed or not on PATH. Install it from https://docs.astral.sh/uv/")
    except subprocess.CalledProcessError:
        fail(failure_message, code=1)


def _print_report_text(report: UpgradeReport) -> None:
    if report.newer_than_installed:
        console.print(
            "[yellow]⚠[/yellow] Project scaffold_version is newer than the installed scaffolder; "
            "skipping upgrade actions."
        )
    for applied in report.automated:
        console.print(f"[green]✓[/green] {applied.kind}: {applied.file}")
    for pending in report.pending:
        console.print(f"[yellow]⚠[/yellow] pending {pending.kind} at {pending.file}:{pending.line}")


def _update_project_impl(
    dry_run: bool,
    *,
    skip_upgrades: bool,
    report: ReportFormat,
    allow_dirty: bool,
) -> None:
    project_root = require_project_root()
    json_mode = report == ReportFormat.json
    runner: UpgradeRunner | None = None

    if not skip_upgrades:
        runner = UpgradeRunner(project_root, dry_run=dry_run, allow_dirty=allow_dirty)
        try:
            upgrade_report = runner.run()
        except RuntimeError as exc:
            fail(str(exc))

        if json_mode:
            sys.stdout.write(json.dumps(upgrade_report.to_json_dict(), indent=2))
            sys.stdout.write("\n")
        else:
            _print_report_text(upgrade_report)

        if not dry_run and upgrade_report.scaffold_version_updated:
            console.print("[green]✓[/green] Updated scaffold_version in pyproject.toml.")

        if dry_run and runner.dry_run_diffs:
            for diff in runner.dry_run_diffs:
                console.print(diff)

    lock_cmd = ["uv", "lock", "--upgrade"]
    sync_cmd = ["uv", "sync"]

    if dry_run:
        if not json_mode:
            console.print("Would run:")
            console.print(f"  {' '.join(lock_cmd)}   (cwd: {project_root})")
            console.print(f"  {' '.join(sync_cmd)}             (cwd: {project_root})")
        return

    _run_uv(lock_cmd, project_root, "Dependency lock failed. See output above.")
    _run_uv(sync_cmd, project_root, "Sync failed. See output above.")

    if not json_mode:
        console.print("[green]✓[/green] Locked updated dependencies.")
        console.print("[green]✓[/green] Synced virtual environment.")


def register(app: typer.Typer) -> None:
    def update_project(
        dry_run: DryRunUpdate = False,
        skip_upgrades: bool = False,
        report: ReportFormat = ReportFormat.text,
        allow_dirty: bool = False,
    ) -> None:
        _update_project_impl(
            dry_run,
            skip_upgrades=skip_upgrades,
            report=report,
            allow_dirty=allow_dirty,
        )

    register_with_alias(
        app,
        "update-project",
        "up",
        update_project,
        help=_GUP,
        epilog=_GUP_EPILOG,
    )
