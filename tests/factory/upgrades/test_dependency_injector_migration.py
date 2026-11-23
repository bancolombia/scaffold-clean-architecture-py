"""dependency-injector → wireup action on the committed 0.5.0 fixture (golden, idempotence, SC metrics)."""

from __future__ import annotations

import difflib
import tomllib
from pathlib import Path

from scaffold_ca_python.factory.upgrades.report import PENDING_KINDS
from tests.factory.upgrades.upgrade_support import (
    GOLDEN,
    LEGACY,
    PINNED_VERSION,
    apply_resolution,
    copy_project,
    migrate,
    reference,
    snapshot,
)


def _changed_lines(before: bytes | None, after: bytes | None) -> int:
    a = (before or b"").decode("utf-8").splitlines()
    b = (after or b"").decode("utf-8").splitlines()
    return sum(
        1
        for line in difflib.unified_diff(a, b, lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    )


def test_fixture_is_a_wired_050_project() -> None:
    config = LEGACY / "src" / "legacy_fixture" / "application" / "config"
    assert "providers.Singleton(" in (config / "usecases_container.py").read_text(encoding="utf-8")
    controller = LEGACY / "src" / "legacy_fixture" / "infrastructure" / "entry_points" / "api" / "v1"
    assert "Depends(Provide[" in (controller / "rest_controller.py").read_text(encoding="utf-8")


def test_migration_matches_golden(tmp_path: Path) -> None:
    root = copy_project(LEGACY, tmp_path / "p")
    report, _ = migrate(root)
    assert snapshot(root) == snapshot(GOLDEN)
    assert [p.kind for p in report.pending] == ["resource_provider"]


def test_migrated_sources_compile() -> None:
    for path in GOLDEN.rglob("*.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_dry_run_writes_nothing_and_prints_relative_diffs(tmp_path: Path) -> None:
    root = copy_project(LEGACY, tmp_path / "p")
    before = snapshot(root)
    report, runner = migrate(root, dry_run=True)
    assert snapshot(root) == before
    assert report.automated
    joined = "".join(runner.diffs)
    assert "--- a/pyproject.toml\n+++ b/pyproject.toml\n" in joined
    assert "+++ b/src/legacy_fixture/application/config/wiring.py\n" in joined
    assert "--- a/src/legacy_fixture/application/config/container.py\n+++ /dev/null\n" in joined
    assert str(tmp_path) not in joined


def test_second_run_writes_nothing_and_reports_pending_again(tmp_path: Path) -> None:
    root = copy_project(GOLDEN, tmp_path / "p")
    before = snapshot(root)
    report, runner = migrate(root)
    assert snapshot(root) == before
    assert runner.touched == []
    assert report.automated == []
    assert [(p.kind, p.file) for p in report.pending] == [
        ("resource_provider", "src/legacy_fixture/application/config/resource_container.py")
    ]


def test_resolved_project_no_longer_matches_the_action(tmp_path: Path) -> None:
    root = reference(tmp_path)
    before = snapshot(root)
    report, _ = migrate(root)
    assert snapshot(root) == before
    assert all(run.skipped for run in report.action_runs)


def test_scaffold_version_written_once_by_the_action(tmp_path: Path) -> None:
    root = copy_project(LEGACY, tmp_path / "p")
    report, _ = migrate(root)
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["scaffold-ca-python"]["scaffold_version"] == PINNED_VERSION
    assert "scaffold_version_updated" not in {a.kind for a in report.automated}


def test_pyproject_tooling_keys_use_real_tables() -> None:
    data = tomllib.loads((GOLDEN / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["pytest"]["ini_options"]["asyncio_mode"] == "auto"
    assert "pytest.ini_options" not in data["tool"]
    assert "ASYNC" in data["tool"]["ruff"]["lint"]["select"]
    assert "TC" in data["tool"]["ruff"]["lint"]["ignore"]
    deps = data["project"]["dependencies"]
    assert not any(d.startswith("dependency-injector") for d in deps)
    assert any(d.startswith("wireup") for d in deps)


def test_sc001_at_least_70_percent_of_required_line_edits_are_automated(tmp_path: Path) -> None:
    """Required = fixture → fully migrated reference; remaining = tool output → reference."""
    fixture, golden, ref = snapshot(LEGACY), snapshot(GOLDEN), snapshot(reference(tmp_path))
    files = fixture.keys() | ref.keys() | golden.keys()
    required = sum(_changed_lines(fixture.get(f), ref.get(f)) for f in files)
    remaining = sum(_changed_lines(golden.get(f), ref.get(f)) for f in files)
    assert required > 100
    assert 1 - remaining / required >= 0.70


def test_remaining_work_is_confined_to_reported_pending_items(tmp_path: Path) -> None:
    golden, ref = snapshot(GOLDEN), snapshot(reference(tmp_path))
    differing = {f for f in golden.keys() | ref.keys() if golden.get(f) != ref.get(f)}
    root = copy_project(GOLDEN, tmp_path / "p")
    report, _ = migrate(root)
    pending_files = {p.file for p in report.pending}
    assert pending_files <= differing
    assert all(p.kind in PENDING_KINDS for p in report.pending)


def test_resolution_overlay_applies_cleanly(tmp_path: Path) -> None:
    root = copy_project(GOLDEN, tmp_path / "p")
    apply_resolution(root)
    assert not (root / "src/legacy_fixture/application/config/resource_container.py").exists()


def test_edited_composition_root_is_pending_and_left_untouched(tmp_path: Path) -> None:
    root = copy_project(LEGACY, tmp_path / "p")
    app = root / "src/legacy_fixture/application/app.py"
    app.write_text(app.read_text(encoding="utf-8") + "\n# local edit\n", encoding="utf-8")
    test_app = root / "src/tests/application/test_app.py"
    before = {app: app.read_bytes(), test_app: test_app.read_bytes()}
    report, _ = migrate(root)
    assert {p: p.read_bytes() for p in before} == before
    assert ("composition_root_modified", "src/legacy_fixture/application/app.py") in {
        (p.kind, p.file) for p in report.pending
    }


def _rename_to_pre_scaffold_layout(root: Path) -> None:
    """Rename ``domain/usecase`` → ``domain/use_cases`` and ``gateways`` → ``gateway`` like older services."""
    pkg = root / "src" / "legacy_fixture"
    (pkg / "domain" / "usecase").rename(pkg / "domain" / "use_cases")
    (pkg / "domain" / "model" / "book" / "gateways").rename(pkg / "domain" / "model" / "book" / "gateway")
    for path in (root / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(".domain.usecase.", ".domain.use_cases.").replace(".gateways.", ".gateway."), encoding="utf-8"
        )


def test_pre_scaffold_naming_variants_are_migrated(tmp_path: Path) -> None:
    root = copy_project(LEGACY, tmp_path / "p")
    _rename_to_pre_scaffold_layout(root)
    report, _ = migrate(root)
    pkg = root / "src" / "legacy_fixture"
    factory = (pkg / "application/config/usecases/get_book_usecase.py").read_text(encoding="utf-8")
    assert "from legacy_fixture.domain.model.book.gateway.book_repository import BookRepository" in factory
    adapter = (pkg / "infrastructure/driven_adapters/book_store/book_store_adapter.py").read_text(encoding="utf-8")
    assert "@wireup.injectable(as_type=BookRepository)" in adapter
    assert [p.kind for p in report.pending] == ["resource_provider"]
    wiring_test = (root / "src/tests/application/config/test_wiring.py").read_text(encoding="utf-8")
    assert "MISSING_ADAPTERS: list[str] = []" in wiring_test
