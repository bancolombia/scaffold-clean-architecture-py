"""Entry-point factory registry."""

from __future__ import annotations

from scaffold_ca_python.factory.entry_points.base import EntryPointFactory
from scaffold_ca_python.factory.entry_points.ep_agent import EntryPointAgent
from scaffold_ca_python.factory.entry_points.ep_generic import EntryPointGeneric
from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp
from scaffold_ca_python.factory.entry_points.ep_restapi import EntryPointRestApi

ENTRY_POINT_FACTORIES: dict[str, type[EntryPointFactory]] = {
    "restapi": EntryPointRestApi,
    "agent": EntryPointAgent,
    "mcp": EntryPointMcp,
    "generic": EntryPointGeneric,
}
