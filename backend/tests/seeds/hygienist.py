from sqlalchemy.ext.asyncio import AsyncSession

from app.hygienists.models import Hygienist


async def seed_hygienist(db: AsyncSession, **overrides) -> Hygienist:
    defaults = dict(first_name="Alice", last_name="Smith")
    h = Hygienist(**{**defaults, **overrides})
    db.add(h)
    await db.flush()
    return h
