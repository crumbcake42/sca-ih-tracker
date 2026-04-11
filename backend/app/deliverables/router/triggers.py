from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deliverables import models, schemas
from app.users.dependencies import PermissionChecker, PermissionName
from app.wa_codes.models import WACode

router = APIRouter(prefix="/{deliverable_id}/triggers", tags=["Deliverable Triggers"])


async def _get_deliverable_or_404(
    deliverable_id: int, db: AsyncSession
) -> models.Deliverable:
    d = await db.get(models.Deliverable, deliverable_id)
    if not d:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return d


@router.get("", response_model=list[schemas.DeliverableWACodeTrigger])
async def list_triggers(
    deliverable_id: int,
    db: AsyncSession = Depends(get_db),
):
    await _get_deliverable_or_404(deliverable_id, db)
    result = await db.execute(
        select(models.DeliverableWACodeTrigger).where(
            models.DeliverableWACodeTrigger.deliverable_id == deliverable_id
        )
    )
    return result.scalars().all()


@router.post(
    "",
    response_model=schemas.DeliverableWACodeTrigger,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def add_trigger(
    deliverable_id: int,
    body: schemas.DeliverableWACodeTriggerCreate,
    db: AsyncSession = Depends(get_db),
):
    await _get_deliverable_or_404(deliverable_id, db)

    wa_code = await db.get(WACode, body.wa_code_id)
    if not wa_code:
        raise HTTPException(status_code=404, detail="WA code not found")

    existing = await db.get(
        models.DeliverableWACodeTrigger, (deliverable_id, body.wa_code_id)
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="This WA code is already a trigger for this deliverable."
        )

    trigger = models.DeliverableWACodeTrigger(
        deliverable_id=deliverable_id, wa_code_id=body.wa_code_id
    )
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    return trigger


@router.delete(
    "/{wa_code_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def remove_trigger(
    deliverable_id: int,
    wa_code_id: int,
    db: AsyncSession = Depends(get_db),
):
    trigger = await db.get(
        models.DeliverableWACodeTrigger, (deliverable_id, wa_code_id)
    )
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    await db.delete(trigger)
    await db.commit()
