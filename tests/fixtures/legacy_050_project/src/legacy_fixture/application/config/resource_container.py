"""Resource DI container — wires infrastructure resources (DB pools, HTTP clients, etc.)."""

from dependency_injector import containers, providers  # noqa: F401

from legacy_fixture.application.config.config import settings  # noqa: F401

# Import resource-level classes here to wire them in the ResourceContainer below.
# legacy_fixture.infrastructure.driven_adapters.my_repo.MyResource


class ResourceContainer(containers.DeclarativeContainer):
    """Wire resource-level singletons (connections, clients) here."""

    # Example:
    # db_pool = providers.Resource(
    #     MyResource,
    #     arg1=settings.ARG1,
    # )
