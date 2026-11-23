"""Book domain model."""

from pydantic import BaseModel


class Book(BaseModel):
    """Book entity."""

    book_id: str
    title: str
