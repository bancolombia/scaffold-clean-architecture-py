"""Tests for scaffold_ca_python.core.version (T091)."""

from __future__ import annotations

from unittest import mock


def test_get_scaffold_version_returns_string() -> None:
    """get_scaffold_version() must return a non-empty string (T091)."""
    from scaffold_ca_python.core.version import get_scaffold_version

    version = get_scaffold_version()
    assert isinstance(version, str)
    assert version  # non-empty


def test_get_scaffold_version_fallback_when_package_not_found() -> None:
    """get_scaffold_version() must return '0.0.0+unknown' when the package is not installed (T091)."""
    from importlib.metadata import PackageNotFoundError

    from scaffold_ca_python.core.version import get_scaffold_version

    with mock.patch("importlib.metadata.version", side_effect=PackageNotFoundError("scaffold-ca-python")):
        version = get_scaffold_version()

    assert version == "0.0.0+unknown"
