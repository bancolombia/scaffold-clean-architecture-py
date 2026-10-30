"""Utilities for managing the test_wiring.py file."""

from __future__ import annotations

import ast
from pathlib import Path


def find_existing_test_function_names(source: str) -> set[str]:
    """Return the set of async def names defined at module level in *source*.

    Used to implement idempotency: skip appending a test stub when a function
    with the same name already exists in test_wiring.py.
    """
    names: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def remove_test_function(source: str, fn_name: str) -> str | None:
    """Remove the named top-level function from *source* and return the result.

    Returns *None* when *fn_name* is not found. Trailing blank lines after the
    removed block are collapsed so the file ends with exactly one newline.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    lines = source.splitlines(keepends=True)
    target = next(
        (
            node
            for node in ast.iter_child_nodes(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name
        ),
        None,
    )
    if target is None:
        return None

    start = target.lineno - 1  # 0-indexed
    end = target.end_lineno  # exclusive (1-indexed end → 0-indexed exclusive)

    # Include leading blank lines that precede the function
    while start > 0 and lines[start - 1].strip() == "":
        start -= 1

    kept = lines[:start] + lines[end:]
    result = "".join(kept).rstrip("\n") + "\n"
    return result


MISSING_ADAPTERS_VAR = "MISSING_ADAPTERS"


def find_missing_adapters(project_root: Path, pkg: str) -> list[str]:
    """Return gateway class names used by use-case factories with no ``as_type=`` adapter.

    Gateways are the names imported from ``...gateways.<module>`` in
    ``application/config/usecases/*.py``; implemented gateways are the ``as_type=<Name>``
    keyword values of decorators found under ``infrastructure/driven_adapters/``.
    """
    base = project_root / "src" / pkg
    used: set[str] = set()
    for path in _py_files(base / "application" / "config" / "usecases"):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ImportFrom) and node.module and ".gateways." in node.module:
                used.update(alias.name for alias in node.names)

    implemented: set[str] = set()
    for path in _py_files(base / "infrastructure" / "driven_adapters"):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "as_type" and isinstance(kw.value, ast.Name):
                        implemented.add(kw.value.id)
    return sorted(used - implemented)


def sync_missing_adapters_marker(wiring_test_path: Path, missing: list[str]) -> bool:
    """Rewrite the ``MISSING_ADAPTERS = [...]`` assignment in *wiring_test_path*.

    Returns True when the file was changed. No-op (False) when the file or the
    assignment does not exist, so projects generated before this marker are untouched.
    """
    if not wiring_test_path.is_file():
        return False
    source = wiring_test_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    target = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == MISSING_ADAPTERS_VAR
        ),
        None,
    )
    if target is None or target.end_lineno is None:
        return False
    items = ", ".join(f'"{name}"' for name in sorted(missing))
    new_line = f"{MISSING_ADAPTERS_VAR}: list[str] = [{items}]\n"
    lines = source.splitlines(keepends=True)
    updated = "".join([*lines[: target.lineno - 1], new_line, *lines[target.end_lineno :]])
    if updated == source:
        return False
    wiring_test_path.write_text(updated, encoding="utf-8")
    return True


def sync_wiring_marker(project_root: Path, pkg: str, tests_root: Path) -> None:
    """Recompute missing adapters and update ``test_wiring.py`` accordingly."""
    sync_missing_adapters_marker(
        tests_root / "application" / "config" / "test_wiring.py",
        find_missing_adapters(project_root, pkg),
    )


def _py_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return [p for p in sorted(directory.rglob("*.py")) if p.is_file()]


def _parse(path: Path) -> ast.AST:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return ast.Module(body=[], type_ignores=[])
