import itertools

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import WACodeLevel
from app.wa_codes.models import WACode

_counter = itertools.count(1)


async def seed_wa_code(
    db: AsyncSession,
    *,
    code: str | None = None,
    level: WACodeLevel = WACodeLevel.PROJECT,
    default_fee: str | None = None,
) -> WACode:
    n = next(_counter)
    resolved_code = code or f"P-{n:03d}"
    wac = WACode(
        code=resolved_code,
        description=f"Description for {resolved_code}",
        level=level,
        default_fee=default_fee,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(wac)
    await db.flush()
    return wac
