"""Tests for BookStoreAdapter."""

from __future__ import annotations

import pytest

from legacy_fixture.infrastructure.driven_adapters.book_store.book_store_adapter import (
    BookStoreAdapter,
)


@pytest.mark.asyncio
async def test_find_by_id_returns_known_book() -> None:
    book = await BookStoreAdapter().find_by_id("1")
    assert book is not None and book.title == "Clean Architecture"


@pytest.mark.asyncio
async def test_find_by_id_returns_none_for_unknown_book() -> None:
    assert await BookStoreAdapter().find_by_id("missing") is None
