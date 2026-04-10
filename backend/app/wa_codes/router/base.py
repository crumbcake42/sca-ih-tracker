from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.factories import create_readonly_router
from app.database import get_db
from app.wa_codes.models import WACode as WACodeModel
from app.wa_codes.schemas import WACode as WACodeSchema

router = APIRouter()

router.include_router(
    create_readonly_router(
        model=WACodeModel,
        read_schema=WACodeSchema,
        default_sort=WACodeModel.code.asc(),
        search_attr=WACodeModel.code,
    )
)


@router.get("/{identifier}", response_model=WACodeSchema)
async def get_wa_code(identifier: str, db: AsyncSession = Depends(get_db)):
    if identifier.isdigit():
        stmt = select(WACodeModel).where(WACodeModel.id == int(identifier))
    else:
        stmt = select(WACodeModel).where(WACodeModel.code == identifier.upper())

    result = await db.execute(stmt)
    wa_code = result.scalar_one_or_none()
    if not wa_code:
        raise HTTPException(status_code=404, detail="WA code not found")
    return wa_code
