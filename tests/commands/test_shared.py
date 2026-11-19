"""Tests for commands/_shared.py."""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from pathlib import Path

import pytest
import typer

from scaffold_ca_python.commands._shared import (
    ensure_absent,
    fail,
    print_dry_run_tree,
    print_pending_dependencies,
    require_project_root,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext

# fail()


def test_fail_exit_code_is_1() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        fail("something went wrong")
    assert exc_info.value.exit_code == 1


def test_fail_with_hint_exits_1() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        fail("bad input", hint="Try again.")
    assert exc_info.value.exit_code == 1


def test_fail_without_hint_exits_1() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        fail("msg")
    assert exc_info.value.exit_code == 1


def test_fail_custom_exit_code() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        fail("dependency step failed", code=2)
    assert exc_info.value.exit_code == 2


# require_project_root()


def test_require_project_root_outside_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Outside a project, prints the standard message and exits 1."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit) as exc_info:
        require_project_root()
    assert exc_info.value.exit_code == 1


def test_require_project_root_none_message_outside_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With not_found_message=None, prints ScaffoldError text and exits 1."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit) as exc_info:
        require_project_root(not_found_message=None)
    assert exc_info.value.exit_code == 1


# ensure_absent()


def test_ensure_absent_file_already_exists(tmp_path: Path) -> None:
    existing = tmp_path / "src" / "thing.py"
    existing.parent.mkdir(parents=True)
    existing.write_text("x")

    with pytest.raises(typer.Exit) as exc_info:
        ensure_absent(existing, tmp_path, kind="File", hint="Choose a different name.")
    assert exc_info.value.exit_code == 1


def test_ensure_absent_directory_already_exists(tmp_path: Path) -> None:
    existing = tmp_path / "src" / "mydir"
    existing.mkdir(parents=True)

    with pytest.raises(typer.Exit) as exc_info:
        ensure_absent(existing, tmp_path, kind="Directory", hint="Remove the directory first.")
    assert exc_info.value.exit_code == 1


def test_ensure_absent_does_nothing_when_path_missing(tmp_path: Path) -> None:
    missing = tmp_path / "not_there.py"
    ensure_absent(missing, tmp_path, kind="File", hint="hint")


# print_dry_run_tree()


def test_print_dry_run_tree(tmp_path: Path) -> None:
    base = tmp_path
    paths: Iterable[Path] = [base / "b.py", base / "a.py", base / "sub" / "c.py"]
    # Should not raise
    print_dry_run_tree("my module", paths, base)


# print_pending_dependencies()


def test_print_pending_dependencies(tmp_path: Path) -> None:
    """Should print Would add lines for pending deps and group deps."""
    ctx = ProjectContext(name="test-app")
    mod = ModuleContext(name="thing", project=ctx)
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=ctx, module_ctx=mod, dry_run=True)
    builder.add_dependency("httpx>=0.27")
    builder.add_dependency("respx>=0.22", group="test")

    # Should not raise
    print_pending_dependencies(builder)


# require_wireup_project guard


def test_require_wireup_project_exits_1_for_legacy(tmp_path: Path) -> None:
    """require_wireup_project must raise typer.Exit(1) for legacy projects."""
    from scaffold_ca_python.commands._shared import require_wireup_project

    ctx = ProjectContext(name="old-app")  # scaffold_version=None → is_legacy=True
    with pytest.raises(typer.Exit) as exc_info:
        require_wireup_project(ctx)
    assert exc_info.value.exit_code == 1


def test_require_wireup_project_message_mentions_manual_migration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """require_wireup_project exit message must explain manual wireup migration."""
    from scaffold_ca_python.commands._shared import require_wireup_project

    ctx = ProjectContext(name="old-app")
    with contextlib.suppress(typer.Exit):
        require_wireup_project(ctx)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "manually" in output.lower()
    assert "wireup" in output.lower()
    assert "scaffold_version" in output
    assert "1.0.0+" in output
    assert "0.6.0" not in output


def test_require_wireup_project_passes_for_wireup_project(tmp_path: Path) -> None:
    """require_wireup_project must not raise for a project with scaffold_version set."""
    from scaffold_ca_python.commands._shared import require_wireup_project

    ctx = ProjectContext(name="my-app", scaffold_version="1.0.0")
    # Should not raise
    require_wireup_project(ctx)
