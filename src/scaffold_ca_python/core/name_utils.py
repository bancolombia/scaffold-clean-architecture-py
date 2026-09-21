"""name_utils: name validation, snake_case, and PascalCase conversion (T021)."""

from __future__ import annotations

import re

NAME_RE = re.compile(r"^[a-z][a-z0-9]*([_-][a-z0-9]+)*$")

# Stricter pattern for module/class-generating commands: snake_case only (no hyphens).
MODULE_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

# Matches transitions: lowercase→uppercase and letter→digit boundary runs
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


class ScaffoldError(Exception):
    """Raised for user-facing errors (exit code 1)."""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def validate_name(name: str) -> str:
    """Validate *name* against the allowed identifier pattern.

    Raises :class:`ScaffoldError` with a hint if the name is invalid.
    Returns the original name unchanged when valid.
    """
    if not NAME_RE.match(name):
        raise ScaffoldError(
            f"Invalid name {name!r}. Use kebab-case (e.g., 'my-project') or snake_case (e.g., 'my_project')."
        )
    return name


def validate_module_name(name: str) -> str:
    """Validate *name* for module/class-generating commands: snake_case only.

    Raises :class:`ScaffoldError` with a hint if the name is not snake_case.
    Returns the original name unchanged when valid.
    """
    if not MODULE_NAME_RE.match(name):
        raise ScaffoldError(f"Invalid name {name!r}. Use snake_case (e.g., 'create_order').")
    return name


def to_snake_case(name: str) -> str:
    """Convert *name* (PascalCase, camelCase, kebab-case, or already snake_case) to snake_case."""
    # Normalise hyphens to underscores first (kebab-case support)
    name = name.replace("-", "_")
    # Insert underscores at camelCase / PascalCase boundaries first
    s = _CAMEL_BOUNDARY_RE.sub("_", name)
    return s.lower()


def to_kebab_case(name: str) -> str:
    """Convert *name* (PascalCase, snake_case, or already kebab-case) to kebab-case."""
    # Normalise underscores to hyphens first (snake_case support)
    name = name.replace("_", "-")
    # Insert hyphens at camelCase / PascalCase boundaries
    s = _CAMEL_BOUNDARY_RE.sub("-", name)
    return s.lower()


def to_pascal_case(name: str) -> str:
    """Convert *name* (snake_case, kebab-case, PascalCase, or single word) to PascalCase."""
    # Normalise hyphens to underscores first (kebab-case support)
    name = name.replace("-", "_")
    # Use [0].upper() + [1:] instead of capitalize() to preserve inner case
    # e.g. "MyOrder" → "MyOrder" (not "Myorder")
    return "".join(part[0].upper() + part[1:] for part in name.split("_") if part)
