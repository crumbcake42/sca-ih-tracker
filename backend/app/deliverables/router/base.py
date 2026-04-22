from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.factories import create_readonly_router
from app.common.guards import assert_deletable
from app.database import get_db
from app.deliverables.models import (
    Deliverable as DeliverableModel,
    DeliverableWACodeTrigger,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.deliverables.schemas import Deliverable as DeliverableSchema

router = APIRouter()

router.include_router(
    create_readonly_router(
        model=DeliverableModel,
        read_schema=DeliverableSchema,
        default_sort=DeliverableModel.name.asc(),
        search_attr=DeliverableModel.name,
    )
)


async def _get_deliverable_references(db: AsyncSession, deliverable_id: int) -> dict[str, int]:
    counts = {}
    for model, label in [
        (ProjectDeliverable, "project_deliverables"),
        (ProjectBuildingDeliverable, "project_building_deliverables"),
        (DeliverableWACodeTrigger, "deliverable_wa_code_triggers"),
    ]:
        count = await db.scalar(
            select(func.count())
            .select_from(model)
            .where(model.deliverable_id == deliverable_id)
        )
        counts[label] = count or 0
    return counts


@router.get("/{deliverable_id}/connections")
async def get_deliverable_connections(
    deliverable_id: int, db: AsyncSession = Depends(get_db)
):
    deliverable = await db.get(DeliverableModel, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return await _get_deliverable_references(db, deliverable_id)


@router.delete("/{deliverable_id}", status_code=204)
async def delete_deliverable(deliverable_id: int, db: AsyncSession = Depends(get_db)):
    deliverable = await db.get(DeliverableModel, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    assert_deletable(await _get_deliverable_references(db, deliverable_id))
    await db.delete(deliverable)
    await db.commit()
