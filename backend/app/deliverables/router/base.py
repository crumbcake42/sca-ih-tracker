from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.factories import create_guarded_delete_router, create_readonly_router
from app.database import get_db
from app.deliverables.models import (
    Deliverable as DeliverableModel,
)
from app.deliverables.models import (
    DeliverableWACodeTrigger,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.deliverables.schemas import Deliverable as DeliverableSchema
from app.deliverables.schemas import DeliverableCreate, DeliverableUpdate
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter()


async def _ensure_name_unique(
    db: AsyncSession, name: str, exclude_id: int | None = None
) -> None:
    stmt = select(DeliverableModel).where(DeliverableModel.name == name)
    if exclude_id is not None:
        stmt = stmt.where(DeliverableModel.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=422, detail=f"name '{name}' already exists.")


router.include_router(
    create_readonly_router(
        model=DeliverableModel,
        read_schema=DeliverableSchema,
        default_sort=DeliverableModel.name.asc(),
        search_attr=DeliverableModel.name,
    )
)


@router.post("/", response_model=DeliverableSchema, status_code=201)
async def create_deliverable(
    data: DeliverableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    await _ensure_name_unique(db, data.name)
    new = DeliverableModel(**data.model_dump(), created_by_id=current_user.id)
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return new


@router.patch("/{deliverable_id}", response_model=DeliverableSchema)
async def update_deliverable(
    deliverable_id: int,
    data: DeliverableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    deliverable = (
        await db.execute(
            select(DeliverableModel).where(DeliverableModel.id == deliverable_id)
        )
    ).scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    updates = data.model_dump(exclude_unset=True)

    if "level" in updates and updates["level"] != deliverable.level:
        raise HTTPException(
            status_code=422, detail="level cannot be changed after creation."
        )

    if "name" in updates and updates["name"] != deliverable.name:
        await _ensure_name_unique(db, updates["name"], exclude_id=deliverable_id)

    for field, value in updates.items():
        setattr(deliverable, field, value)
    deliverable.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(deliverable)
    return deliverable


router.include_router(
    create_guarded_delete_router(
        model=DeliverableModel,
        not_found_detail="Deliverable not found",
        refs=[
            (ProjectDeliverable, ProjectDeliverable.deliverable_id, "project_deliverables"),
            (ProjectBuildingDeliverable, ProjectBuildingDeliverable.deliverable_id, "project_building_deliverables"),
            (DeliverableWACodeTrigger, DeliverableWACodeTrigger.deliverable_id, "deliverable_wa_code_triggers"),
        ],
        path_param_name="deliverable_id",
    )
)
