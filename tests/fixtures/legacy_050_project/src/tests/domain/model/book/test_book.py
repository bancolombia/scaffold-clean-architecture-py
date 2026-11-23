"""Tests for Book model."""

from legacy_fixture.domain.model.book.book import Book


def test_book_can_be_instantiated() -> None:
    assert Book(book_id="1", title="T").title == "T"
