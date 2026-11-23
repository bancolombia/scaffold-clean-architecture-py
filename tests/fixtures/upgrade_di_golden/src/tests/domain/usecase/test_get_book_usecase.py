"""Tests for GetBookUseCase."""

import pytest

from legacy_fixture.domain.model.book.book import Book
from legacy_fixture.domain.model.book.gateways.book_repository import BookRepository
from legacy_fixture.domain.usecase.get_book_usecase import GetBookUseCase


class _FakeRepository(BookRepository):
    async def find_by_id(self, book_id: str) -> Book | None:
        return Book(book_id=book_id, title="Fake")


@pytest.mark.asyncio
async def test_get_book_returns_repository_result() -> None:
    use_case = GetBookUseCase(book_repository=_FakeRepository())
    book = await use_case.execute("42")
    assert book is not None and book.book_id == "42"
