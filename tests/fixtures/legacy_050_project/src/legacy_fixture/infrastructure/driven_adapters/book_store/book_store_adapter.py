"""BookStore async driven adapter."""

from __future__ import annotations

from legacy_fixture.domain.model.book.book import Book
from legacy_fixture.domain.model.book.gateways.book_repository import BookRepository

_BOOKS = {"1": Book(book_id="1", title="Clean Architecture")}


class BookStoreAdapter(BookRepository):
    """In-memory driven adapter for BookStore."""

    async def find_by_id(self, book_id: str) -> Book | None:
        """Return the stored book, if any."""
        return _BOOKS.get(book_id)
