"""Utilities for managing the test_wiring.py file."""

from __future__ import annotations

import ast


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
