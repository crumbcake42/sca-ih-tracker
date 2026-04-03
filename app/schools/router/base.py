# app/schools/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.common.factories import create_readonly_router
from app.database import get_db
from app.schools.models import School
from app.schools.schemas import SchoolCreate, School as SchoolRead

router = APIRouter()


router.include_router(
    create_readonly_router(
        model=School,
        read_schema=SchoolRead,
        # prefix="/list",
        default_sort=School.code.asc(),
        search_attr=School.code,
    )
)


# @router.get("/", response_model=list[SchoolRead])
# async def list_schools(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(School))
#     return result.scalars().all()


@router.get("/{identifier}", response_model=SchoolRead)
async def get_school(identifier: str, db: AsyncSession = Depends(get_db)):
    # 1. Try to treat identifier as an integer ID
    if identifier.isdigit():
        stmt = select(School).where(School.id == int(identifier))
    else:
        # 2. Otherwise, treat it as a unique School Code
        stmt = select(School).where(School.code == identifier.upper())

    result = await db.execute(stmt)
    school = result.scalar_one_or_none()

    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school
