from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.lab_results.models import (
    SampleSubtype,
    SampleType,
    SampleTypeRequiredRole,
    SampleTypeWACode,
    SampleUnitType,
    TurnaroundOption,
)
from app.lab_results.schemas import (
    SampleSubtypeCreate,
    SampleSubtypeRead,
    SampleTypeCreate,
    SampleTypeRead,
    SampleTypeRequiredRoleCreate,
    SampleTypeRequiredRoleRead,
    SampleTypeUpdate,
    SampleTypeWACodeCreate,
    SampleTypeWACodeRead,
    SampleUnitTypeCreate,
    SampleUnitTypeRead,
    TurnaroundOptionCreate,
    TurnaroundOptionRead,
)
from app.lab_results.service import get_sample_type_or_404
from app.users.dependencies import PermissionChecker, PermissionName
from app.wa_codes.models import WACode

router = APIRouter(prefix="/config/sample-types", tags=["Lab Results — Config"])

_edit = [Depends(PermissionChecker(PermissionName.PROJECT_EDIT))]


# ---------------------------------------------------------------------------
# Sample type CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=list[SampleTypeRead])
async def list_sample_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SampleType).order_by(SampleType.name))
    return result.scalars().all()


@router.post("", response_model=SampleTypeRead, status_code=status.HTTP_201_CREATED,
             dependencies=_edit)
async def create_sample_type(body: SampleTypeCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(SampleType).where(SampleType.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Sample type name already exists")
    st = SampleType(**body.model_dump())
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st


@router.get("/{type_id}", response_model=SampleTypeRead)
async def get_sample_type(type_id: int, db: AsyncSession = Depends(get_db)):
    return await get_sample_type_or_404(type_id, db)


@router.patch("/{type_id}", response_model=SampleTypeRead, dependencies=_edit)
async def update_sample_type(
    type_id: int, body: SampleTypeUpdate, db: AsyncSession = Depends(get_db)
):
    st = await get_sample_type_or_404(type_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(st, field, value)
    await db.commit()
    await db.refresh(st)
    return st


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_edit)
async def delete_sample_type(type_id: int, db: AsyncSession = Depends(get_db)):
    st = await get_sample_type_or_404(type_id, db)
    await db.delete(st)
    await db.commit()


# ---------------------------------------------------------------------------
# Subtypes
# ---------------------------------------------------------------------------


@router.post("/{type_id}/subtypes", response_model=SampleSubtypeRead,
             status_code=status.HTTP_201_CREATED, dependencies=_edit)
async def add_subtype(
    type_id: int, body: SampleSubtypeCreate, db: AsyncSession = Depends(get_db)
):
    await get_sample_type_or_404(type_id, db)
    subtype = SampleSubtype(sample_type_id=type_id, name=body.name)
    db.add(subtype)
    await db.commit()
    await db.refresh(subtype)
    return subtype


@router.delete("/{type_id}/subtypes/{subtype_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=_edit)
async def remove_subtype(
    type_id: int, subtype_id: int, db: AsyncSession = Depends(get_db)
):
    subtype = await db.get(SampleSubtype, subtype_id)
    if not subtype or subtype.sample_type_id != type_id:
        raise HTTPException(status_code=404, detail="Subtype not found")
    await db.delete(subtype)
    await db.commit()


# ---------------------------------------------------------------------------
# Unit types
# ---------------------------------------------------------------------------


@router.post("/{type_id}/unit-types", response_model=SampleUnitTypeRead,
             status_code=status.HTTP_201_CREATED, dependencies=_edit)
async def add_unit_type(
    type_id: int, body: SampleUnitTypeCreate, db: AsyncSession = Depends(get_db)
):
    await get_sample_type_or_404(type_id, db)
    ut = SampleUnitType(sample_type_id=type_id, name=body.name)
    db.add(ut)
    await db.commit()
    await db.refresh(ut)
    return ut


@router.delete("/{type_id}/unit-types/{unit_type_id}",
               status_code=status.HTTP_204_NO_CONTENT, dependencies=_edit)
async def remove_unit_type(
    type_id: int, unit_type_id: int, db: AsyncSession = Depends(get_db)
):
    ut = await db.get(SampleUnitType, unit_type_id)
    if not ut or ut.sample_type_id != type_id:
        raise HTTPException(status_code=404, detail="Unit type not found")
    await db.delete(ut)
    await db.commit()


# ---------------------------------------------------------------------------
# Turnaround options
# ---------------------------------------------------------------------------


@router.post("/{type_id}/turnaround-options", response_model=TurnaroundOptionRead,
             status_code=status.HTTP_201_CREATED, dependencies=_edit)
async def add_turnaround_option(
    type_id: int, body: TurnaroundOptionCreate, db: AsyncSession = Depends(get_db)
):
    await get_sample_type_or_404(type_id, db)
    tat = TurnaroundOption(sample_type_id=type_id, hours=body.hours, label=body.label)
    db.add(tat)
    await db.commit()
    await db.refresh(tat)
    return tat


@router.delete("/{type_id}/turnaround-options/{option_id}",
               status_code=status.HTTP_204_NO_CONTENT, dependencies=_edit)
async def remove_turnaround_option(
    type_id: int, option_id: int, db: AsyncSession = Depends(get_db)
):
    tat = await db.get(TurnaroundOption, option_id)
    if not tat or tat.sample_type_id != type_id:
        raise HTTPException(status_code=404, detail="Turnaround option not found")
    await db.delete(tat)
    await db.commit()


# ---------------------------------------------------------------------------
# Required roles
# ---------------------------------------------------------------------------


@router.post("/{type_id}/required-roles", response_model=SampleTypeRequiredRoleRead,
             status_code=status.HTTP_201_CREATED, dependencies=_edit)
async def add_required_role(
    type_id: int, body: SampleTypeRequiredRoleCreate, db: AsyncSession = Depends(get_db)
):
    await get_sample_type_or_404(type_id, db)
    existing = await db.execute(
        select(SampleTypeRequiredRole).where(
            SampleTypeRequiredRole.sample_type_id == type_id,
            SampleTypeRequiredRole.role_type == body.role_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Role already required for this sample type")
    rr = SampleTypeRequiredRole(sample_type_id=type_id, role_type=body.role_type)
    db.add(rr)
    await db.commit()
    await db.refresh(rr)
    return rr


@router.delete("/{type_id}/required-roles/{required_role_id}",
               status_code=status.HTTP_204_NO_CONTENT, dependencies=_edit)
async def remove_required_role(
    type_id: int, required_role_id: int, db: AsyncSession = Depends(get_db)
):
    rr = await db.get(SampleTypeRequiredRole, required_role_id)
    if not rr or rr.sample_type_id != type_id:
        raise HTTPException(status_code=404, detail="Required role not found")
    await db.delete(rr)
    await db.commit()


# ---------------------------------------------------------------------------
# WA code requirements
# ---------------------------------------------------------------------------


@router.post("/{type_id}/wa-codes", response_model=SampleTypeWACodeRead,
             status_code=status.HTTP_201_CREATED, dependencies=_edit)
async def add_wa_code(
    type_id: int, body: SampleTypeWACodeCreate, db: AsyncSession = Depends(get_db)
):
    await get_sample_type_or_404(type_id, db)
    wa_code = await db.get(WACode, body.wa_code_id)
    if not wa_code:
        raise HTTPException(status_code=404, detail="WA code not found")
    existing = await db.get(
        SampleTypeWACode,
        {"sample_type_id": type_id, "wa_code_id": body.wa_code_id},
    )
    if existing:
        raise HTTPException(status_code=409, detail="WA code already required for this sample type")
    link = SampleTypeWACode(sample_type_id=type_id, wa_code_id=body.wa_code_id)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.delete("/{type_id}/wa-codes/{wa_code_id}",
               status_code=status.HTTP_204_NO_CONTENT, dependencies=_edit)
async def remove_wa_code(
    type_id: int, wa_code_id: int, db: AsyncSession = Depends(get_db)
):
    link = await db.get(
        SampleTypeWACode,
        {"sample_type_id": type_id, "wa_code_id": wa_code_id},
    )
    if not link:
        raise HTTPException(status_code=404, detail="WA code requirement not found")
    await db.delete(link)
    await db.commit()
