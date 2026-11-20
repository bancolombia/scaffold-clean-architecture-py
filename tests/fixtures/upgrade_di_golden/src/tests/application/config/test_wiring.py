"""Tests for the wireup DI container."""

from __future__ import annotations

import pytest
from wireup.errors import WireupError

from legacy_fixture.application.config.wiring import create_container

# Gateways required by use-case factories that no adapter implements yet.
# Maintained by `scaffold guc`, `scaffold gda` and `scaffold dm`; do not edit by hand.
# While non-empty, wireup rejects the whole graph, so every test here is an expected failure.
MISSING_ADAPTERS: list[str] = []

pytestmark = pytest.mark.xfail(
    bool(MISSING_ADAPTERS),
    raises=WireupError,
    strict=True,
    reason="No adapter implements: " + ", ".join(MISSING_ADAPTERS) + ". Run `scaffold gda --gateway <gateway>`.",
)


async def test_container_creates_successfully() -> None:
    """create_container() must build the whole dependency graph."""
    container = create_container()
    await container.close()
