"""Tests for server entry point — legacy-fixture."""
from __future__ import annotations

import importlib


def test_start_server_is_callable() -> None:
    from legacy_fixture.application.app import start_server

    assert callable(start_server)


def test_server_module_imports_without_error() -> None:
    mod = importlib.import_module("legacy_fixture.server")
    assert mod is not None
