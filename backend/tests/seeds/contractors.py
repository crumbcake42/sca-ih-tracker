import itertools

from sqlalchemy.ext.asyncio import AsyncSession

from app.contractors.models import Contractor

_counter = itertools.count(1)


async def seed_contractor(db: AsyncSession, **overrides) -> Contractor:
    n = next(_counter)
    defaults = dict(
        name=overrides.pop("name", f"Test Contractor {n}"),
        address=overrides.pop("address", "123 Main St"),
        city=overrides.pop("city", "New York"),
        state=overrides.pop("state", "NY"),
        zip_code=overrides.pop("zip_code", "10001"),
    )
    c = Contractor(**defaults, **overrides)
    db.add(c)
    await db.flush()
    return c
