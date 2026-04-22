from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.factories import create_readonly_router
from app.common.guards import assert_deletable
from app.database import get_db
from app.deliverables.models import DeliverableWACodeTrigger
from app.lab_results.models import SampleTypeWACode
from app.users.dependencies import get_current_user
from app.users.models import User
from app.wa_codes.models import WACode as WACodeModel
from app.wa_codes.schemas import WACode as WACodeSchema
from app.wa_codes.schemas import WACodeCreate, WACodeUpdate
from app.work_auths.models import (
    RFABuildingCode,
    RFAProjectCode,
    WorkAuthBuildingCode,
    WorkAuthProjectCode,
)

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


async def _ensure_code_unique(
    db: AsyncSession, code: str, exclude_id: int | None = None
) -> None:
    stmt = select(WACodeModel).where(WACodeModel.code == code)
    if exclude_id is not None:
        stmt = stmt.where(WACodeModel.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=422, detail=f"code '{code}' already exists.")


async def _ensure_description_unique(
    db: AsyncSession, description: str, exclude_id: int | None = None
) -> None:
    stmt = select(WACodeModel).where(WACodeModel.description == description)
    if exclude_id is not None:
        stmt = stmt.where(WACodeModel.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=422, detail="description already exists."
        )


@router.post("/", response_model=WACodeSchema, status_code=201)
async def create_wa_code(
    data: WACodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_code_unique(db, data.code)
    await _ensure_description_unique(db, data.description)
    new_wa_code = WACodeModel(**data.model_dump(), created_by_id=current_user.id)
    db.add(new_wa_code)
    await db.commit()
    await db.refresh(new_wa_code)
    return new_wa_code


@router.patch("/{wa_code_id}", response_model=WACodeSchema)
async def update_wa_code(
    wa_code_id: int,
    data: WACodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WACodeModel).where(WACodeModel.id == wa_code_id)
    )
    wa_code = result.scalar_one_or_none()
    if not wa_code:
        raise HTTPException(status_code=404, detail="WA code not found")

    updates = data.model_dump(exclude_unset=True)

    # Level is immutable once set: changing it would invalidate every
    # downstream record that gated validation on the original level.
    if "level" in updates and updates["level"] != wa_code.level:
        raise HTTPException(
            status_code=422, detail="level cannot be changed after creation."
        )

    if "code" in updates and updates["code"] != wa_code.code:
        await _ensure_code_unique(db, updates["code"], exclude_id=wa_code_id)

    if "description" in updates and updates["description"] != wa_code.description:
        await _ensure_description_unique(
            db, updates["description"], exclude_id=wa_code_id
        )

    for field, value in updates.items():
        setattr(wa_code, field, value)
    wa_code.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(wa_code)
    return wa_code


async def _get_wa_code_references(db: AsyncSession, wa_code_id: int) -> dict[str, int]:
    counts = {}
    for model, label in [
        (WorkAuthProjectCode, "work_auth_project_codes"),
        (WorkAuthBuildingCode, "work_auth_building_codes"),
        (RFAProjectCode, "rfa_project_codes"),
        (RFABuildingCode, "rfa_building_codes"),
        (DeliverableWACodeTrigger, "deliverable_wa_code_triggers"),
        (SampleTypeWACode, "sample_type_wa_codes"),
    ]:
        count = await db.scalar(
            select(func.count()).select_from(model).where(model.wa_code_id == wa_code_id)
        )
        counts[label] = count or 0
    return counts


@router.get("/{wa_code_id}/connections")
async def get_wa_code_connections(wa_code_id: int, db: AsyncSession = Depends(get_db)):
    wa_code = await db.get(WACodeModel, wa_code_id)
    if not wa_code:
        raise HTTPException(status_code=404, detail="WA code not found")
    return await _get_wa_code_references(db, wa_code_id)


@router.delete("/{wa_code_id}", status_code=204)
async def delete_wa_code(wa_code_id: int, db: AsyncSession = Depends(get_db)):
    wa_code = await db.get(WACodeModel, wa_code_id)
    if not wa_code:
        raise HTTPException(status_code=404, detail="WA code not found")
    assert_deletable(await _get_wa_code_references(db, wa_code_id))
    await db.delete(wa_code)
    await db.commit()
