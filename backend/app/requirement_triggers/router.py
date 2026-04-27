from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.common.requirements import registry
from app.requirement_triggers.models import WACodeRequirementTrigger
from app.requirement_triggers.schemas import (
    WACodeRequirementTriggerCreate,
    WACodeRequirementTriggerRead,
)
from app.requirement_triggers.services import hash_template_params
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User
from app.wa_codes.models import WACode

router = APIRouter(prefix="/requirement-triggers", tags=["Requirement Triggers"])


async def _get_wa_code_or_404(wa_code_id: int, db: AsyncSession) -> WACode:
    wc = await db.get(WACode, wa_code_id)
    if not wc:
        raise HTTPException(status_code=404, detail="WA code not found")
    return wc


@router.get("", response_model=list[WACodeRequirementTriggerRead])
async def list_requirement_triggers(
    wa_code_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WACodeRequirementTrigger)
    if wa_code_id is not None:
        stmt = stmt.where(WACodeRequirementTrigger.wa_code_id == wa_code_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "",
    response_model=WACodeRequirementTriggerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement_trigger(
    payload: WACodeRequirementTriggerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    await _get_wa_code_or_404(payload.wa_code_id, db)

    try:
        registry.get(payload.requirement_type_name)
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown requirement type: '{payload.requirement_type_name}'.",
        )

    params_hash = hash_template_params(payload.template_params)

    existing = await db.execute(
        select(WACodeRequirementTrigger).where(
            WACodeRequirementTrigger.wa_code_id == payload.wa_code_id,
            WACodeRequirementTrigger.requirement_type_name == payload.requirement_type_name,
            WACodeRequirementTrigger.template_params_hash == params_hash,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A trigger with this WA code, requirement type, and template params already exists.",
        )

    trigger = WACodeRequirementTrigger(
        wa_code_id=payload.wa_code_id,
        requirement_type_name=payload.requirement_type_name,
        template_params=payload.template_params,
        template_params_hash=params_hash,
        created_by_id=current_user.id,
    )
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    return trigger


@router.delete(
    "/{trigger_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def delete_requirement_trigger(
    trigger_id: int,
    db: AsyncSession = Depends(get_db),
):
    trigger = await db.get(WACodeRequirementTrigger, trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    await db.delete(trigger)
    await db.commit()
