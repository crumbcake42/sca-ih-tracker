from pydantic import BaseModel
from typing import Optional


class ImportErrorReport(BaseModel):
    row: int
    msg: str
    context: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized wrapper for 400/500 level API errors"""

    detail: str
    code: str
