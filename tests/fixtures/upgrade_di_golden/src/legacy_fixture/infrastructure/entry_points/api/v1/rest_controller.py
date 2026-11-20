"""REST controller — versioned API router for legacy-fixture."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from wireup import Injected

from legacy_fixture.domain.usecase.get_book_usecase import GetBookUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1")


@router.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "app is online"})


@router.get("/books/{book_id}")
async def get_book(
    book_id: str,
    use_case: Injected[GetBookUseCase],
) -> JSONResponse:
    """Return a book by id."""
    book = await use_case.execute(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return JSONResponse(content=book.model_dump())
