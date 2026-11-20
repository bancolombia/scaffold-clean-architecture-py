"""Use-case DI container."""
from dependency_injector import containers, providers

from legacy_fixture.domain.usecase.get_book_usecase import GetBookUseCase


class UseCaseContainer(containers.DeclarativeContainer):
    """Wire use-case singletons here, injecting driven adapters."""

    da_container = providers.DependenciesContainer()

    get_book = providers.Singleton(
        GetBookUseCase,
        book_repository=da_container.book_store,
    )
