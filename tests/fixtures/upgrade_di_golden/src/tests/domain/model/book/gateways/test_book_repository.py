"""Tests for BookRepository gateway."""

from abc import ABC

from legacy_fixture.domain.model.book.gateways.book_repository import BookRepository


def test_book_repository_is_abstract_contract() -> None:
    assert issubclass(BookRepository, ABC)
