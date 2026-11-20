"""Driven-adapters DI container."""
from dependency_injector import containers, providers

from legacy_fixture.infrastructure.driven_adapters.book_store.book_store_adapter import BookStoreAdapter


class DAContainer(containers.DeclarativeContainer):
    """Wire infrastructure driven-adapter singletons here."""

    book_store = providers.Singleton(BookStoreAdapter)
