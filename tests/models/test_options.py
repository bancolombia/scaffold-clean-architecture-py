"""Tests for EntryPointOptions ( / )."""

from __future__ import annotations

import pytest

from scaffold_ca_python.models.options import EntryPointOptions


def test_entry_point_options_is_frozen() -> None:
    opts = EntryPointOptions(type_="restapi")
    from dataclasses import FrozenInstanceError  # noqa: PLC0415

    with pytest.raises(FrozenInstanceError):
        opts.type_ = "mcp"  # type: ignore[misc]


def test_creation_flags_returns_only_active_flags() -> None:
    opts = EntryPointOptions(type_="restapi", swagger="f.yaml", enable_kafka=True)
    flags = opts.creation_flags()
    assert "--swagger" in flags
    assert "--enable-kafka" in flags
    assert "--enable-mcp-client" not in flags
    assert "--with-resources" not in flags
    assert "--with-prompts" not in flags


def test_creation_flags_order() -> None:
    opts = EntryPointOptions(
        type_="mcp",
        swagger="f.yaml",
        enable_kafka=True,
        enable_mcp_client=True,
        with_resources=True,
        with_prompts=True,
    )
    flags = opts.creation_flags()
    expected_order = ["--swagger", "--enable-kafka", "--enable-mcp-client", "--with-resources", "--with-prompts"]
    assert flags == expected_order


def test_creation_flags_empty_when_no_flags() -> None:
    opts = EntryPointOptions(type_="generic")
    assert opts.creation_flags() == []


def test_apply_to_sets_builder_params() -> None:
    from unittest.mock import MagicMock

    builder = MagicMock()
    opts = EntryPointOptions(
        type_="agent",
        enable_kafka=True,
        enable_mcp_client=True,
        with_resources=True,
        with_prompts=False,
    )
    routes: list[tuple[str, str]] = [("/x", "get")]
    opts.apply_to(builder, routes)

    builder.add_param.assert_any_call("enable_kafka", True)
    builder.add_param.assert_any_call("enable_mcp_client", True)
    builder.add_param.assert_any_call("with_resources", True)
    builder.add_param.assert_any_call("with_prompts", False)
    builder.add_param.assert_any_call("routes", routes)
