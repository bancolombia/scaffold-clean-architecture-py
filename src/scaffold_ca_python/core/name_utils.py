"""name_utils: name validation, snake_case, and PascalCase conversion."""

from __future__ import annotations

import re

from scaffold_ca_python.core.errors import ScaffoldError

NAME_RE = re.compile(r"^[a-z][a-z0-9]*([_-][a-z0-9]+)*$")

# Stricter pattern for module/class-generating commands: snake_case only (no hyphens).
MODULE_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

# Trailing _usecase / _use_case segments; strip_usecase_suffix prefixes "_" before matching.
_USECASE_SUFFIX_RE = re.compile(r"(?:_(?:usecase|use_case))+$")

# Matches transitions: lowercase→uppercase and letter→digit boundary runs
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


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


def validate_snake_identifier(value: str, *, kind: str) -> str:
    """Return *value* when it is a valid snake_case identifier; otherwise raise ValueError."""
    if not MODULE_NAME_RE.fullmatch(value):
        raise ValueError(f"Invalid {kind} {value!r}. Use snake_case.")
    return value


def validate_module_name(name: str) -> str:
    """Validate *name* for module/class-generating commands: snake_case only.

    Raises :class:`ScaffoldError` with a hint if the name is not snake_case.
    Returns the original name unchanged when valid.
    """
    try:
        validate_snake_identifier(name, kind="name")
    except ValueError as exc:
        raise ScaffoldError(str(exc)) from None
    return name


def _case_convert(name: str, sep: str) -> str:
    other = "-" if sep == "_" else "_"
    name = name.replace(other, sep)
    return _CAMEL_BOUNDARY_RE.sub(sep, name).lower()


def to_snake_case(name: str) -> str:
    """Convert *name* (PascalCase, camelCase, kebab-case, or already snake_case) to snake_case."""
    return _case_convert(name, "_")


def strip_usecase_suffix(name: str) -> str:
    """Remove every trailing ``_usecase`` / ``_use_case`` suffix from *name* (may return an empty string)."""
    return _USECASE_SUFFIX_RE.sub("", f"_{name}").removeprefix("_")


def to_kebab_case(name: str) -> str:
    """Convert *name* (PascalCase, snake_case, or already kebab-case) to kebab-case."""
    return _case_convert(name, "-")


def to_pascal_case(name: str) -> str:
    """Convert *name* (snake_case, kebab-case, PascalCase, or single word) to PascalCase."""
    # Normalise hyphens to underscores first (kebab-case support)
    name = name.replace("-", "_")
    # Use [0].upper() + [1:] instead of capitalize() to preserve inner case
    # e.g. "MyOrder" → "MyOrder" (not "Myorder")
    return "".join(part[0].upper() + part[1:] for part in name.split("_") if part)
