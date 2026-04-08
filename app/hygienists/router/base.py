from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.hygienists.models import Hygienist as HygienistModel
from app.hygienists.schemas import Hygienist, HygienistCreate, HygienistUpdate

router = APIRouter()


@router.get("/", response_model=list[Hygienist])
async def list_hygienists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HygienistModel).order_by(
            HygienistModel.last_name, HygienistModel.first_name
        )
    )
    return result.scalars().all()


@router.get("/{hygienist_id}", response_model=Hygienist)
async def get_hygienist(hygienist_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HygienistModel).where(HygienistModel.id == hygienist_id)
    )
    hygienist = result.scalar_one_or_none()
    if not hygienist:
        raise HTTPException(status_code=404, detail="Hygienist not found")
    return hygienist


@router.post("/", response_model=Hygienist, status_code=201)
async def create_hygienist(
    data: HygienistCreate, db: AsyncSession = Depends(get_db)
):
    new_hygienist = HygienistModel(**data.model_dump())
    db.add(new_hygienist)
    await db.commit()
    await db.refresh(new_hygienist)
    return new_hygienist


@router.patch("/{hygienist_id}", response_model=Hygienist)
async def update_hygienist(
    hygienist_id: int, data: HygienistUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(HygienistModel).where(HygienistModel.id == hygienist_id)
    )
    hygienist = result.scalar_one_or_none()
    if not hygienist:
        raise HTTPException(status_code=404, detail="Hygienist not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(hygienist, field, value)

    await db.commit()
    await db.refresh(hygienist)
    return hygienist


@router.delete("/{hygienist_id}", status_code=204)
async def delete_hygienist(hygienist_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HygienistModel).where(HygienistModel.id == hygienist_id)
    )
    hygienist = result.scalar_one_or_none()
    if not hygienist:
        raise HTTPException(status_code=404, detail="Hygienist not found")

    await db.delete(hygienist)
    await db.commit()
