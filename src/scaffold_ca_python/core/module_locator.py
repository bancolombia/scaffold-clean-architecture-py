"""Locate module source and test files across the CA directory structure."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.project_detector import resolve_tests_root


def find_module_targets(project_root: Path, pkg: str, snake: str) -> list[tuple[Path, Path | None]]:
    """Return ``(src_path, test_path | None)`` pairs for every match of *snake*.

    Searches in order: domain/model, domain/usecase, driven_adapters,
    entry_points, helpers.
    """
    src_root = project_root / "src" / pkg
    tests_root = resolve_tests_root(project_root)

    candidates: list[tuple[Path, Path | None]] = []

    for src_rel, test_rel in [
        (src_root / "domain" / "model" / f"{snake}.py", tests_root / "domain" / "model" / f"test_{snake}.py"),
        (src_root / "domain" / "usecase" / f"{snake}.py", tests_root / "domain" / "usecase" / f"test_{snake}.py"),
    ]:
        if src_rel.exists():
            candidates.append((src_rel, test_rel if test_rel.exists() else None))

    for src_rel, test_rel in [
        (
            src_root / "infrastructure" / "driven_adapters" / snake,
            tests_root / "infrastructure" / "driven_adapters" / snake,
        ),
        (
            src_root / "infrastructure" / "entry_points" / snake,
            tests_root / "infrastructure" / "entry_points" / snake,
        ),
        (
            src_root / "infrastructure" / "helpers" / snake,
            tests_root / "infrastructure" / "helpers" / snake,
        ),
    ]:
        if src_rel.exists():
            candidates.append((src_rel, test_rel if test_rel.exists() else None))

    return candidates
