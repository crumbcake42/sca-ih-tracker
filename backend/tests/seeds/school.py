import itertools

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro
from app.schools.models import School

_counter = itertools.count(1)


async def seed_school(db: AsyncSession, *, code: str | None = None, **overrides) -> School:
    n = next(_counter)
    resolved_code = code or f"K{n:03d}"
    school = School(
        code=resolved_code,
        name=overrides.pop("name", f"School {resolved_code}"),
        address=overrides.pop("address", "1 Test St"),
        city=overrides.pop("city", Boro.BROOKLYN),
        state=overrides.pop("state", "NY"),
        zip_code=overrides.pop("zip_code", "11201"),
        **overrides,
    )
    db.add(school)
    await db.flush()
    return school
