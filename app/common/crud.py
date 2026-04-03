from typing import Type, TypeVar, Sequence, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


async def get_paginated_list(
    db: AsyncSession,
    model: Type[ModelT],
    skip: int = 0,
    limit: int = 50,
    sort_by: Any | None = None,
    search_attr: Any | None = None,
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
