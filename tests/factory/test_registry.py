"""Tests for the factory registry dispatch tables.

Verifies each factory registry has the expected keys and that dispatching an unknown
type fails with an error that lists the valid keys.
"""

from __future__ import annotations

from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from scaffold_ca_python.commands import (
    delete_module,
    generate_helper,
    generate_model,
    generate_use_case,
)
from scaffold_ca_python.factory.driven_adapters import DRIVEN_ADAPTER_FACTORIES
from scaffold_ca_python.factory.entry_points import ENTRY_POINT_FACTORIES
from tests.helpers import strip_ansi

runner = CliRunner()


def test_entry_point_registry_keys() -> None:
    assert set(ENTRY_POINT_FACTORIES) == {"restapi", "agent", "mcp", "generic"}


def test_driven_adapter_registry_keys() -> None:
    assert set(DRIVEN_ADAPTER_FACTORIES) == {"rest-consumer", "secrets", "generic", "sqlalchemy", "psycopg"}


def test_simple_commands_have_no_registry() -> None:
    assert not hasattr(generate_model, "_REGISTRY")
    assert not hasattr(generate_use_case, "_REGISTRY")
    assert not hasattr(generate_helper, "_REGISTRY")
    assert not hasattr(delete_module, "_REGISTRY")


def test_gep_unknown_type_lists_valid_keys() -> None:
    result = runner.invoke(app, ["gep", "--type", "bogus"], catch_exceptions=False)
    assert result.exit_code == 1
    # Flatten soft-wrapped console output so key tokens stay intact.
    out = strip_ansi(result.output).replace("\n", " ")
    for key in ENTRY_POINT_FACTORIES:
        assert key in out, f"Expected valid key '{key}' listed in error output"


def test_gda_unknown_type_lists_valid_keys() -> None:
    result = runner.invoke(app, ["gda", "--type", "bogus"], catch_exceptions=False)
    assert result.exit_code == 1
    out = strip_ansi(result.output).replace("\n", " ")
    for key in DRIVEN_ADAPTER_FACTORIES:
        assert key in out, f"Expected valid key '{key}' listed in error output"


# : factory ClassVar descriptors and PIPELINE_PROVIDERS


def test_factory_descriptors() -> None:
    """Verify ClassVar descriptor values for all registered entry-point factories."""
    from scaffold_ca_python.factory.entry_points import ENTRY_POINT_FACTORIES  # noqa: PLC0415
    from scaffold_ca_python.factory.entry_points.base import EntryPointFlag  # noqa: PLC0415

    ep = ENTRY_POINT_FACTORIES

    # restapi
    assert ep["restapi"].subdir == "api/v1"
    assert ep["restapi"].supported_flags == frozenset({EntryPointFlag.SWAGGER})
    conflict_types = {c.type_key for c in ep["restapi"].conflicts}
    assert "mcp" in conflict_types
    assert "agent" in conflict_types

    # mcp
    assert ep["mcp"].subdir == "mcp_server"
    assert ep["mcp"].supported_flags == frozenset({EntryPointFlag.MCP_PRIMITIVES})
    mcp_conflict_types = {c.type_key for c in ep["mcp"].conflicts}
    assert mcp_conflict_types == {"restapi", "agent"}

    # agent
    assert ep["agent"].subdir == "a2a_server"
    assert ep["agent"].supported_flags == frozenset()
    agent_conflict_types = {c.type_key for c in ep["agent"].conflicts}
    assert agent_conflict_types == {"restapi", "mcp"}

    # generic
    assert ep["generic"].subdir == "generic"
    assert ep["generic"].supported_flags == frozenset()
    assert ep["generic"].conflicts == ()


def test_driven_adapter_descriptors() -> None:
    """Verify fixed_name for all driven-adapter factories."""
    from scaffold_ca_python.factory.driven_adapters import DRIVEN_ADAPTER_FACTORIES  # noqa: PLC0415

    da = DRIVEN_ADAPTER_FACTORIES
    assert da["rest-consumer"].fixed_name == "rest_consumer"
    assert da["secrets"].fixed_name == "secrets"
    assert da["generic"].fixed_name is None
    assert da["sqlalchemy"].fixed_name == "sqlalchemy"
    assert da["psycopg"].fixed_name == "psycopg"


def test_pipeline_providers_keys_in_order() -> None:
    """PIPELINE_PROVIDERS must have keys 'github' and 'azure' in that order."""
    from scaffold_ca_python.factory.pipelines import PIPELINE_PROVIDERS  # noqa: PLC0415

    keys = list(PIPELINE_PROVIDERS.keys())
    assert keys == ["github", "azure"]
