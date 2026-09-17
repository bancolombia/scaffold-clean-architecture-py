"""Tests for the command _REGISTRY dispatch tables (T042 / 015-factory-builder-refactor).

Verifies each command exposes a factory registry keyed by its supported types, and
that dispatching an unknown type fails with an error that lists the valid keys.
"""

from __future__ import annotations

from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from scaffold_ca_python.commands import (
    delete_module,
    generate_driven_adapter,
    generate_entry_point,
    generate_helper,
    generate_model,
    generate_use_case,
)
from tests.conftest import strip_ansi

runner = CliRunner()


def test_entry_point_registry_keys() -> None:
    assert set(generate_entry_point._REGISTRY) == {"restapi", "agent", "mcp", "generic"}


def test_driven_adapter_registry_keys() -> None:
    assert set(generate_driven_adapter._REGISTRY) == {"rest-consumer", "secrets", "generic"}


def test_simple_command_registries_expose_single_key() -> None:
    assert set(generate_model._REGISTRY) == {"model"}
    assert set(generate_use_case._REGISTRY) == {"use_case"}
    assert set(generate_helper._REGISTRY) == {"helper"}
    assert set(delete_module._REGISTRY) == {"delete"}


def test_gep_unknown_type_lists_valid_keys() -> None:
    result = runner.invoke(app, ["gep", "--type", "bogus"], catch_exceptions=False)
    assert result.exit_code == 1
    # Flatten soft-wrapped console output so key tokens stay intact.
    out = strip_ansi(result.output).replace("\n", " ")
    for key in generate_entry_point._REGISTRY:
        assert key in out, f"Expected valid key '{key}' listed in error output"


def test_gda_unknown_type_lists_valid_keys() -> None:
    result = runner.invoke(app, ["gda", "--type", "bogus"], catch_exceptions=False)
    assert result.exit_code == 1
    out = strip_ansi(result.output).replace("\n", " ")
    for key in generate_driven_adapter._REGISTRY:
        assert key in out, f"Expected valid key '{key}' listed in error output"
