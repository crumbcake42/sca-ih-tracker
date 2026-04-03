from typing import Annotated, Any, TypeVar, TypeAlias, Generic
from pydantic import BeforeValidator, BaseModel


T = TypeVar("T")


def empty_to_none(v: Any) -> Any:
    """If the value is an empty or whitespace-only string, return None."""
    if isinstance(v, str) and not v.strip():
        return None
    return v


# The Generic Alias
# This allows you to use OptionalField[str], OptionalField[EmailStr], etc.
OptionalField: TypeAlias = Annotated[T | None, BeforeValidator(empty_to_none)]

# Pre-defined aliases for common use cases
OptionalString = OptionalField[str]


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
