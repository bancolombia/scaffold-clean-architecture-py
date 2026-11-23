"""update_project: upgrade actions, then dependency refresh via uv."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Annotated, TextIO

import typer

from scaffold_ca_python.commands._shared import (
    DryRunUpdate,
    auto_format_project,
    console,
    fail,
    register_with_alias,
    require_project_root,
)
from scaffold_ca_python.factory.upgrades.report import UpgradeReport
from scaffold_ca_python.factory.upgrades.runner import UpgradeError, UpgradeRunner

_GUP = "Run upgrade actions, then refresh dependencies via uv lock --upgrade + uv sync. Alias: 'up'"
_GUP_EPILOG = (
    "Example:\n\n  * scaffold up --dry-run\n\n  * scaffold up --report json\n\n"
    "  * scaffold update-project --skip-upgrades"
)


class ReportFormat(StrEnum):
    text = "text"
    json = "json"


@contextmanager
def _human_output_to_stderr(enabled: bool) -> Iterator[None]:
    """Route Rich output to stderr so stdout carries only the JSON report."""
    previous = console.stderr
    console.stderr = enabled or previous
    try:
        yield
    finally:
        console.stderr = previous


def _stderr_fd() -> int:
    """File descriptor for stderr, or DEVNULL when stderr is not a real file (e.g. under a test runner)."""
    try:
        return sys.stderr.fileno()
    except (AttributeError, OSError, ValueError):
        return subprocess.DEVNULL


def _run_uv(cmd: list[str], cwd: Path, failure_message: str, *, json_mode: bool) -> None:
    try:
        subprocess.run(cmd, check=True, cwd=cwd, stdout=_stderr_fd() if json_mode else None)
    except FileNotFoundError:
        fail("'uv' is not installed or not on PATH. Install it from https://docs.astral.sh/uv/")
    except subprocess.CalledProcessError:
        fail(failure_message)


def _print_report_text(report: UpgradeReport) -> None:
    if report.newer_than_installed:
        console.print(
            "[yellow]⚠[/yellow] Project scaffold_version is newer than the installed scaffolder; "
            "skipping upgrade actions."
        )
    for applied in report.automated:
        console.print(f"[green]✓[/green] {applied.kind}: {applied.file}", highlight=False, soft_wrap=True)
    for pending in report.pending:
        console.print(
            f"[yellow]⚠[/yellow] pending {pending.kind} at {pending.file}:{pending.line} "
            f"(guide: #{pending.guide_section})",
            highlight=False,
            soft_wrap=True,
        )
    if report.pending:
        console.print(
            "[dim]Resolve pending items with docs/migration/dependency-injector-to-wireup.md "
            "or `scaffold install-skill migrate-di`.[/dim]"
        )


def _write_diffs(diffs: list[str], stream: TextIO) -> None:
    for diff in diffs:
        stream.write(diff)
    stream.flush()


def _run_upgrades(project_root: Path, *, dry_run: bool, allow_dirty: bool, json_mode: bool) -> None:
    runner = UpgradeRunner(project_root, dry_run=dry_run, allow_dirty=allow_dirty)
    try:
        report = runner.run()
    except UpgradeError as exc:
        fail(str(exc))
    if runner.touched:
        auto_format_project(project_root, runner.touched)
    if dry_run:
        _write_diffs(runner.diffs, sys.stderr if json_mode else sys.stdout)
    if json_mode:
        sys.stdout.write(json.dumps(report.to_json_dict(), indent=2) + "\n")
        sys.stdout.flush()
    else:
        _print_report_text(report)


def _update_project_impl(dry_run: bool, *, skip_upgrades: bool, report: ReportFormat, allow_dirty: bool) -> None:
    json_mode = report == ReportFormat.json
    with _human_output_to_stderr(json_mode):
        project_root = require_project_root()
        if not skip_upgrades:
            _run_upgrades(project_root, dry_run=dry_run, allow_dirty=allow_dirty, json_mode=json_mode)

        lock_cmd = ["uv", "lock", "--upgrade"]
        sync_cmd = ["uv", "sync"]
        if dry_run:
            console.print("Would run:")
            console.print(f"  {' '.join(lock_cmd)}   (cwd: {project_root})")
            console.print(f"  {' '.join(sync_cmd)}             (cwd: {project_root})")
            return

        _run_uv(lock_cmd, project_root, "Dependency lock failed. See output above.", json_mode=json_mode)
        _run_uv(sync_cmd, project_root, "Sync failed. See output above.", json_mode=json_mode)
        console.print("[green]✓[/green] Locked updated dependencies.")
        console.print("[green]✓[/green] Synced virtual environment.")


def register(app: typer.Typer) -> None:
    def update_project(
        dry_run: DryRunUpdate = False,
        skip_upgrades: Annotated[
            bool, typer.Option("--skip-upgrades", help="Skip upgrade actions; only refresh dependencies.")
        ] = False,
        report: Annotated[
            ReportFormat, typer.Option("--report", help="Report format; json prints only JSON on stdout.")
        ] = ReportFormat.text,
        allow_dirty: Annotated[
            bool, typer.Option("--allow-dirty", help="Allow upgrade writes on a dirty or non-git tree.")
        ] = False,
    ) -> None:
        _update_project_impl(dry_run, skip_upgrades=skip_upgrades, report=report, allow_dirty=allow_dirty)

    register_with_alias(app, "update-project", "up", update_project, help=_GUP, epilog=_GUP_EPILOG)
