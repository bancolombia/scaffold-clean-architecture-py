"""Scaffolder version helpers."""

from __future__ import annotations

import importlib.metadata


def get_scaffold_version() -> str:
    """Return the installed version of scaffold-ca-python.

    Falls back to ``"0.0.0+unknown"`` when the package metadata is unavailable
    (e.g. during editable installs where the metadata has not been generated yet).
    """
    try:
        return importlib.metadata.version("scaffold-ca-python")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+unknown"
