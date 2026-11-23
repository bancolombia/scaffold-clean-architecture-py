"""GetBook use case."""

from legacy_fixture.domain.model.book.book import Book
from legacy_fixture.domain.model.book.gateways.book_repository import BookRepository


class GetBookUseCase:
    """GetBook async use case."""

    def __init__(self, book_repository: BookRepository) -> None:
        self._book_repository = book_repository

    async def execute(self, book_id: str) -> Book | None:
        """Execute the use case."""
        return await self._book_repository.find_by_id(book_id)
