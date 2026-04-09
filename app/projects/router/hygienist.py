from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.crud import get_by_ids
from app.database import get_db
from app.hygienists.models import Hygienist
from app.projects import models, schemas
from app.schools.models import School
from app.users.dependencies import PermissionChecker, PermissionName

router = APIRouter(prefix="/{project_id}/hygienist", tags=["Projects Hygienist"])

# ---------------------------------------------------------------------------
# Hygienist assignment
# ---------------------------------------------------------------------------


async def _get_project_or_404(project_id: int, db: AsyncSession) -> models.Project:
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.hygienist_link))
        .where(models.Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post(
    "",
    response_model=schemas.HygienistAssignment,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def assign_hygienist(
    project_id: int,
    body: schemas.AssignHygienist,
    db: AsyncSession = Depends(get_db),
):
    """Assign a hygienist to a project. Replaces any existing assignment."""
    project = await _get_project_or_404(project_id, db)

    hygienist = await db.get(Hygienist, body.hygienist_id)
    if not hygienist:
        raise HTTPException(status_code=404, detail="Hygienist not found")

    if project.hygienist_link:
        # Replace existing assignment in-place rather than deleting and
        # reinserting — keeps the same row and just updates the FK.
        project.hygienist_link.hygienist_id = body.hygienist_id
    else:
        project.hygienist_link = models.ProjectHygienistLink(
            project_id=project_id, hygienist_id=body.hygienist_id
        )

    await db.commit()
    await db.refresh(project.hygienist_link)
    return project.hygienist_link


@router.get("", response_model=schemas.HygienistAssignment)
async def get_hygienist_assignment(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get the hygienist currently assigned to a project."""
    project = await _get_project_or_404(project_id, db)
    if not project.hygienist_link:
        raise HTTPException(
            status_code=404, detail="No hygienist assigned to this project"
        )
    return project.hygienist_link


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def remove_hygienist(project_id: int, db: AsyncSession = Depends(get_db)):
    """Remove the hygienist assignment from a project."""
    project = await _get_project_or_404(project_id, db)
    if not project.hygienist_link:
        raise HTTPException(
            status_code=404, detail="No hygienist assigned to this project"
        )

    await db.delete(project.hygienist_link)
    await db.commit()
    await db.refresh(project)
    return None
