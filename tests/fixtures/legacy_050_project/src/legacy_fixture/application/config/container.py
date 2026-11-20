"""Root application DI container."""

from dependency_injector import containers, providers

from legacy_fixture.application.config.driven_adapters_container import DAContainer
from legacy_fixture.application.config.resource_container import ResourceContainer
from legacy_fixture.application.config.usecases_container import UseCaseContainer


class Container(containers.DeclarativeContainer):
    """Top-level container wiring all sub-containers."""

    resource_container = providers.Container(ResourceContainer)
    da_container = providers.Container(DAContainer)
    usecase_container = providers.Container(
        UseCaseContainer,
        da_container=da_container,
    )
