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


# ---------------------------------------------------------------------------
# T013: factory ClassVar descriptors and PIPELINE_PROVIDERS
# ---------------------------------------------------------------------------


def test_factory_descriptors() -> None:
    """Verify ClassVar descriptor values for all registered entry-point factories."""
    from scaffold_ca_python.factory.entry_points.base import EntryPointFlag  # noqa: PLC0415

    from scaffold_ca_python.factory.entry_points import ENTRY_POINT_FACTORIES  # noqa: PLC0415

    ep = ENTRY_POINT_FACTORIES

    # restapi
    assert ep["restapi"].subdir == "api/v1"
    assert EntryPointFlag.SWAGGER in ep["restapi"].supported_flags
    assert EntryPointFlag.ENABLE_MCP_CLIENT in ep["restapi"].supported_flags
    assert EntryPointFlag.ENABLE_KAFKA in ep["restapi"].supported_flags
    conflict_labels = {c.label for c in ep["restapi"].conflicts}
    assert "mcp_server" in conflict_labels
    assert "agent" in conflict_labels

    # mcp
    assert ep["mcp"].subdir == "mcp_server"
    assert EntryPointFlag.MCP_PRIMITIVES in ep["mcp"].supported_flags
    assert EntryPointFlag.ENABLE_KAFKA in ep["mcp"].supported_flags
    mcp_conflict_subdirs = {c.subdir for c in ep["mcp"].conflicts}
    assert "api" in mcp_conflict_subdirs

    # agent
    assert ep["agent"].subdir == "agent"
    assert EntryPointFlag.ENABLE_MCP_CLIENT in ep["agent"].supported_flags
    assert EntryPointFlag.ENABLE_KAFKA in ep["agent"].supported_flags
    agent_conflict_subdirs = {c.subdir for c in ep["agent"].conflicts}
    assert "api" in agent_conflict_subdirs

    # generic
    assert ep["generic"].subdir == "generic"
    assert EntryPointFlag.ENABLE_MCP_CLIENT in ep["generic"].supported_flags
    assert EntryPointFlag.ENABLE_KAFKA in ep["generic"].supported_flags
    assert ep["generic"].conflicts == ()


def test_driven_adapter_descriptors() -> None:
    """Verify fixed_name for all driven-adapter factories."""
    from scaffold_ca_python.factory.driven_adapters import DRIVEN_ADAPTER_FACTORIES  # noqa: PLC0415

    da = DRIVEN_ADAPTER_FACTORIES
    assert da["rest-consumer"].fixed_name == "rest_consumer"
    assert da["secrets"].fixed_name == "secrets"
    assert da["generic"].fixed_name is None


def test_pipeline_providers_keys_in_order() -> None:
    """PIPELINE_PROVIDERS must have keys 'github' and 'azure' in that order."""
    from scaffold_ca_python.factory.pipelines import PIPELINE_PROVIDERS  # noqa: PLC0415

    keys = list(PIPELINE_PROVIDERS.keys())
    assert keys == ["github", "azure"]
