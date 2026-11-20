"""Driven-adapters DI container."""

from dependency_injector import containers, providers  # noqa: F401

# Import driven-adapter classes here to wire them in the DAContainer below.
# legacy_fixture.infrastructure.driven_adapters.my_repo.MyRepo


class DAContainer(containers.DeclarativeContainer):
    """Wire infrastructure driven-adapter singletons here."""

    # Example:
    # my_repo = providers.Singleton(
    #     MyRepo,
    #     arg1=arg1,
    # )
