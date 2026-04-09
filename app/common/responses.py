from typing import Generic, TypeVar

from pydantic import BaseModel

from app.common.errors import ImportErrorReport

T = TypeVar("T")


class BatchImportResponse(BaseModel, Generic[T]):
    """The TypeScript equivalent of BatchImportResponse<T>"""

    message: str
    created_count: int
    created_items: list[T]
    errors: list["ImportErrorReport"]  # Forward reference to errors.py logic if needed
