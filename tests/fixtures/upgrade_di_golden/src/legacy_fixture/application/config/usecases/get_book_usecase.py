"""Factory for GetBookUseCase — migrated from the dependency-injector container."""

from __future__ import annotations

import wireup

from legacy_fixture.domain.model.book.gateways.book_repository import BookRepository
from legacy_fixture.domain.usecase.get_book_usecase import GetBookUseCase


@wireup.injectable
def get_book_usecase_factory(
    book_repository: BookRepository,
) -> GetBookUseCase:
    """Construct GetBookUseCase with its dependencies."""
    return GetBookUseCase(
        book_repository=book_repository,
    )
