from collections.abc import Sequence
from typing import Any, Protocol, TypeVar

from fastapi import HTTPException
from sqlalchemy import func, select, ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped

from app.database import Base


class HasIntPK(Protocol):
    id: Mapped[int]


IntPKModelT = TypeVar("IntPKModelT", bound=HasIntPK)
ModelT = TypeVar("ModelT", bound=Base)


async def get_by_ids(
    db: AsyncSession,
    model: type[IntPKModelT],
    ids: list[int],
) -> list[IntPKModelT]:
    """
    Fetch records by a list of primary key IDs.
    Raises 404 if any IDs are not found.
    """
    result = await db.execute(select(model).where(model.id.in_(ids)))  # type: ignore[attr-defined]
    items = result.scalars().all()

    if len(items) != len(ids):
        found_ids = {item.id for item in items}
        missing = [i for i in ids if i not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"{model.__name__}(s) not found: {missing}",
        )
    return list(items)


async def get_paginated_list(
    db: AsyncSession,
    model: type[ModelT],
    skip: int = 0,
    limit: int = 50,
    sort_by: ColumnElement[Any] | None = None,
    search_attr: ColumnElement[str] | None = None,
    search_query: str | None = None,
) -> tuple[Sequence[ModelT], int]:

    stmt = select(model)

    # Apply search filter if provided
    if search_attr is not None and search_query:
        stmt = stmt.where(search_attr.ilike(f"%{search_query}%"))

    # Count must reflect the filtered total, not the whole table
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Apply Sort and Pagination
    if sort_by is not None:
        stmt = stmt.order_by(sort_by)

    result = await db.execute(stmt.offset(skip).limit(limit))
    items = result.scalars().all()

    return items, total
