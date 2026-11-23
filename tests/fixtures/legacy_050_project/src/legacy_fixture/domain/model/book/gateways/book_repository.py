"""Book gateway."""

from abc import ABC, abstractmethod

from legacy_fixture.domain.model.book.book import Book


class BookRepository(ABC):
    """Repository contract for Book. Add the operations your domain needs."""

    @abstractmethod
    async def find_by_id(self, book_id: str) -> Book | None:
        """Return the book with *book_id*, or None."""
