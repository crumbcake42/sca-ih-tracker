from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.projects import models, schemas
from app.users.dependencies import PermissionChecker, PermissionName, get_current_user
from app.users.models import User

router = APIRouter(prefix="/{project_id}/manager", tags=["Projects Manager"])


async def _get_project_or_404(project_id: int, db: AsyncSession) -> models.Project:
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.manager_assignments))
        .where(models.Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post(
    "",
    response_model=schemas.ManagerAssignment,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def assign_manager(
    project_id: int,
    body: schemas.AssignManager,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assign a manager to a project.

    If a manager is already assigned, their record is closed (unassigned_at is
    set) before the new assignment is inserted. The history is never deleted.
    """
    project = await _get_project_or_404(project_id, db)

    manager = await db.get(User, body.user_id)
    if not manager:
        raise HTTPException(status_code=404, detail="User not found")

    # Close the current active assignment if one exists.
    active = project.active_manager
    if active:
        if active.user_id == body.user_id:
            raise HTTPException(
                status_code=409,
                detail="This user is already the active manager for this project.",
            )
        active.unassigned_at = datetime.now(timezone.utc)

    new_assignment = models.ProjectManagerAssignment(
        project_id=project_id,
        user_id=body.user_id,
        assigned_by_id=current_user.id,
    )
    project.manager_assignments.append(new_assignment)
    await db.commit()
    await db.refresh(new_assignment)
    return new_assignment


@router.get("", response_model=schemas.ManagerAssignment)
async def get_active_manager(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get the currently active manager assignment for a project."""
    project = await _get_project_or_404(project_id, db)
    if not project.active_manager:
        raise HTTPException(
            status_code=404, detail="No manager assigned to this project"
        )
    return project.active_manager


@router.get("/history", response_model=list[schemas.ManagerAssignment])
async def get_manager_history(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get the full manager assignment history for a project, newest first."""
    project = await _get_project_or_404(project_id, db)
    return sorted(
        project.manager_assignments,
        key=lambda a: (a.assigned_at, a.id),
        reverse=True,
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def unassign_manager(project_id: int, db: AsyncSession = Depends(get_db)):
    """Close the active manager assignment without assigning a replacement."""
    project = await _get_project_or_404(project_id, db)
    if not project.active_manager:
        raise HTTPException(
            status_code=404, detail="No manager assigned to this project"
        )

    project.active_manager.unassigned_at = datetime.now(timezone.utc)
    await db.commit()
    return None
