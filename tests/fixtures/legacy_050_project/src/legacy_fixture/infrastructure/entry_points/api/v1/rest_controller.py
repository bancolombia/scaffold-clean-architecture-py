"""REST controller — versioned API router for legacy-fixture."""
from __future__ import annotations

import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from legacy_fixture.application.config.container import Container
from legacy_fixture.domain.usecase.get_book_usecase import GetBookUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1")


@router.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "app is online"})


@router.get("/books/{book_id}")
@inject
async def get_book(
    book_id: str,
    use_case: GetBookUseCase = Depends(Provide[Container.usecase_container.get_book]),
) -> JSONResponse:
    """Return a book by id."""
    book = await use_case.execute(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return JSONResponse(content=book.model_dump())
