"""Extensibility proof for factory registries (T044 / SC-002).

A new module type must be addable by registering a ModuleFactory under a fresh key in
a command's `_REGISTRY`, with no edits to the command file itself. Here a stub factory
is registered under a new key and the command is shown to dispatch to it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from scaffold_ca_python.commands import generate_entry_point
from scaffold_ca_python.core.module_builder import ModuleBuilder

runner = CliRunner()


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Scaffold a real `my-app` project inside tmp_path."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    return project_dir


def test_new_type_routes_to_registered_factory(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Registering a new ModuleFactory key routes `gep` to it without editing the command."""
    calls: list[str] = []

    class _StubFactory:
        def build(self, builder: ModuleBuilder) -> None:
            calls.append("built")

    # Add a brand-new type key; monkeypatch reverts the registry after the test.
    monkeypatch.setitem(generate_entry_point._REGISTRY, "stub", _StubFactory)

    result = runner.invoke(app, ["gep", "--type", "stub", "--dry-run"], catch_exceptions=False)

    assert result.exit_code == 0
    assert calls == ["built"], "Registered stub factory's build() was not invoked"
