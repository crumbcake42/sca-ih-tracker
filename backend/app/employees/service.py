from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.employees.models import Employee


async def generate_unique_display_name(
    db: AsyncSession,
    first_name: str,
    last_name: str,
    preferred: str | None = None,
    exclude_id: int | None = None,
) -> str:
    base = preferred or f"{first_name} {last_name}"
    stmt = select(Employee.display_name).where(Employee.display_name.like(f"{base}%"))
    if exclude_id is not None:
        stmt = stmt.where(Employee.id != exclude_id)
    taken = set((await db.execute(stmt)).scalars().all())
    if base not in taken:
        return base
    n = 2
    while f"{base} {n}" in taken:
        n += 1
    return f"{base} {n}"
