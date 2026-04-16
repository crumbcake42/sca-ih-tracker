from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import InternalDeliverableStatus, NoteEntityType, SCADeliverableStatus
from app.database import get_db
from app.deliverables import schemas as deliverable_schemas
from app.deliverables.models import (
    Deliverable,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.notes.models import Note
from app.projects.models import Project
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter()

# Statuses that require no unresolved blocking notes on the deliverable.
_BLOCKED_INTERNAL = {InternalDeliverableStatus.IN_REVIEW}
_BLOCKED_SCA = {SCADeliverableStatus.UNDER_REVIEW, SCADeliverableStatus.APPROVED}


async def _check_no_blocking_notes(deliverable_id: int, db: AsyncSession) -> None:
    """Raise 422 if there are unresolved blocking notes on this deliverable."""
    result = await db.execute(
        select(Note).where(
            Note.entity_type == NoteEntityType.DELIVERABLE,
            Note.entity_id == deliverable_id,
            Note.is_blocking.is_(True),
            Note.is_resolved.is_(False),
            Note.parent_note_id.is_(None),
        )
    )
    blocking = result.scalars().all()
    if blocking:
        count = len(blocking)
        raise HTTPException(
            status_code=422,
            detail=f"Cannot advance deliverable status: {count} unresolved blocking note(s) must be resolved first.",
        )


async def _get_project_or_404(project_id: int, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ---------------------------------------------------------------------------
# Project-level deliverables — /projects/{project_id}/deliverables
# ---------------------------------------------------------------------------


@router.get(
    "/{project_id}/deliverables",
    response_model=list[deliverable_schemas.ProjectDeliverable],
)
async def list_project_deliverables(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    await _get_project_or_404(project_id, db)
    result = await db.execute(
        select(ProjectDeliverable).where(ProjectDeliverable.project_id == project_id)
    )
    return result.scalars().all()


@router.post(
    "/{project_id}/deliverables",
    response_model=deliverable_schemas.ProjectDeliverable,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_deliverable(
    project_id: int,
    body: deliverable_schemas.ProjectDeliverableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    await _get_project_or_404(project_id, db)

    deliverable = await db.get(Deliverable, body.deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    existing = await db.get(ProjectDeliverable, (project_id, body.deliverable_id))
    if existing:
        raise HTTPException(
            status_code=409,
            detail="This deliverable is already tracked for this project.",
        )

    pd = ProjectDeliverable(
        project_id=project_id,
        deliverable_id=body.deliverable_id,
        internal_status=body.internal_status,
        sca_status=body.sca_status,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(pd)
    await db.commit()
    await db.refresh(pd)
    return pd


@router.patch(
    "/{project_id}/deliverables/{deliverable_id}",
    response_model=deliverable_schemas.ProjectDeliverable,
)
async def update_project_deliverable(
    project_id: int,
    deliverable_id: int,
    body: deliverable_schemas.ProjectDeliverableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    pd = await db.get(ProjectDeliverable, (project_id, deliverable_id))
    if not pd:
        raise HTTPException(status_code=404, detail="Project deliverable not found")
    if body.internal_status in _BLOCKED_INTERNAL or body.sca_status in _BLOCKED_SCA:
        await _check_no_blocking_notes(deliverable_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pd, field, value)
    pd.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(pd)
    return pd


@router.delete(
    "/{project_id}/deliverables/{deliverable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def delete_project_deliverable(
    project_id: int,
    deliverable_id: int,
    db: AsyncSession = Depends(get_db),
):
    pd = await db.get(ProjectDeliverable, (project_id, deliverable_id))
    if not pd:
        raise HTTPException(status_code=404, detail="Project deliverable not found")
    await db.delete(pd)
    await db.commit()


# ---------------------------------------------------------------------------
# Building-level deliverables — /projects/{project_id}/building-deliverables
# ---------------------------------------------------------------------------


@router.get(
    "/{project_id}/building-deliverables",
    response_model=list[deliverable_schemas.ProjectBuildingDeliverable],
)
async def list_building_deliverables(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    await _get_project_or_404(project_id, db)
    result = await db.execute(
        select(ProjectBuildingDeliverable).where(
            ProjectBuildingDeliverable.project_id == project_id
        )
    )
    return result.scalars().all()


@router.post(
    "/{project_id}/building-deliverables",
    response_model=deliverable_schemas.ProjectBuildingDeliverable,
    status_code=status.HTTP_201_CREATED,
)
async def add_building_deliverable(
    project_id: int,
    body: deliverable_schemas.ProjectBuildingDeliverableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    await _get_project_or_404(project_id, db)

    deliverable = await db.get(Deliverable, body.deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    check = await db.execute(
        text(
            "SELECT 1 FROM project_school_links "
            "WHERE project_id = :pid AND school_id = :sid"
        ),
        {"pid": project_id, "sid": body.school_id},
    )
    if not check.fetchone():
        raise HTTPException(
            status_code=422, detail="School is not linked to this project."
        )

    existing = await db.get(
        ProjectBuildingDeliverable, (project_id, body.deliverable_id, body.school_id)
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="This deliverable is already tracked for this project and school.",
        )

    bd = ProjectBuildingDeliverable(
        project_id=project_id,
        deliverable_id=body.deliverable_id,
        school_id=body.school_id,
        internal_status=body.internal_status,
        sca_status=body.sca_status,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(bd)
    await db.commit()
    await db.refresh(bd)
    return bd


@router.patch(
    "/{project_id}/building-deliverables/{deliverable_id}/{school_id}",
    response_model=deliverable_schemas.ProjectBuildingDeliverable,
)
async def update_building_deliverable(
    project_id: int,
    deliverable_id: int,
    school_id: int,
    body: deliverable_schemas.ProjectBuildingDeliverableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    bd = await db.get(
        ProjectBuildingDeliverable, (project_id, deliverable_id, school_id)
    )
    if not bd:
        raise HTTPException(status_code=404, detail="Building deliverable not found")
    if body.internal_status in _BLOCKED_INTERNAL or body.sca_status in _BLOCKED_SCA:
        await _check_no_blocking_notes(deliverable_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(bd, field, value)
    bd.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(bd)
    return bd


@router.delete(
    "/{project_id}/building-deliverables/{deliverable_id}/{school_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def delete_building_deliverable(
    project_id: int,
    deliverable_id: int,
    school_id: int,
    db: AsyncSession = Depends(get_db),
):
    bd = await db.get(
        ProjectBuildingDeliverable, (project_id, deliverable_id, school_id)
    )
    if not bd:
        raise HTTPException(status_code=404, detail="Building deliverable not found")
    await db.delete(bd)
    await db.commit()
