# app/schools/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.factories import create_readonly_router
from app.database import get_db
from app.schools.models import School
from app.schools.schemas import School as SchoolRead
from app.schools.schemas import SchoolCreate, SchoolUpdate
from app.users.dependencies import get_current_user
from app.users.models import User

router = APIRouter()


router.include_router(
    create_readonly_router(
        model=School,
        read_schema=SchoolRead,
        default_sort=School.code.asc(),
        search_attr=School.code,
    )
)


async def _ensure_code_unique(db: AsyncSession, code: str) -> None:
    existing = (
        await db.execute(select(School).where(School.code == code))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=422, detail=f"code '{code}' already exists.")


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


@router.post("/", response_model=SchoolRead, status_code=201)
async def create_school(
    data: SchoolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_code_unique(db, data.code)
    new_school = School(**data.model_dump(), created_by_id=current_user.id)
    db.add(new_school)
    await db.commit()
    await db.refresh(new_school)
    return new_school


@router.patch("/{school_id}", response_model=SchoolRead)
async def update_school(
    school_id: int,
    data: SchoolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    updates = data.model_dump(exclude_unset=True)
    if "code" in updates and updates["code"] != school.code:
        await _ensure_code_unique(db, updates["code"])

    for field, value in updates.items():
        setattr(school, field, value)
    school.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(school)
    return school
