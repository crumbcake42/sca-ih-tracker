
from pydantic import BaseModel


class ImportErrorReport(BaseModel):
    row: int
    msg: str
    context: str | None = None


class ErrorResponse(BaseModel):
    """Standardized wrapper for 400/500 level API errors"""

    detail: str
    code: str
