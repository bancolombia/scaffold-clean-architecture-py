"""Resource DI container — wires infrastructure resources (DB pools, HTTP clients, etc.)."""
from dependency_injector import containers, providers

from legacy_fixture.infrastructure.helpers.clock.clock import open_clock


class ResourceContainer(containers.DeclarativeContainer):
    """Wire resource-level singletons (connections, clients) here."""

    clock = providers.Resource(open_clock)
