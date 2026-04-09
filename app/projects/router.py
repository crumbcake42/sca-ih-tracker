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

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=list[schemas.Project])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    name_search: str | None = Query(None, description="Filter by project name"),
    db: AsyncSession = Depends(get_db),
):
    """Get project list with optional pagination and search."""
    stmt = select(models.Project).options(selectinload(models.Project.schools))

    if name_search:
        stmt = stmt.where(models.Project.name.ilike(f"%{name_search}%"))

    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.post(
    "/",
    response_model=schemas.Project,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_CREATE))],
)
async def create_project(
    project_in: schemas.ProjectCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new project (Requires PROJECT_CREATE permission)."""
    schools = await get_by_ids(db, School, project_in.school_ids)

    new_project = models.Project(
        **project_in.model_dump(exclude={"school_ids"}),
        schools=schools,
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project


@router.get("/{project_id}", response_model=schemas.Project)
async def get_project_by_id(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single project with its related School, Contractor, and Hygienist details."""
    stmt = (
        select(models.Project)
        .options(selectinload(models.Project.schools))
        .options(selectinload(models.Project.contractor))
        .options(selectinload(models.Project.hygienist_link))
        .where(models.Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch(
    "/{project_id}",
    response_model=schemas.Project,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def update_project(
    project_id: int,
    project_update: schemas.ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Update project details (Requires PROJECT_EDIT permission)."""
    stmt = (
        select(models.Project)
        .options(selectinload(models.Project.schools))
        .where(models.Project.id == project_id)
    )
    result = await db.execute(stmt)
    db_project = result.scalar_one_or_none()

    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.model_dump(exclude_unset=True, exclude={"school_ids"})
    for key, value in update_data.items():
        setattr(db_project, key, value)

    if "school_ids" in project_update.model_fields_set:
        db_project.schools = await get_by_ids(db, School, project_update.school_ids)

    await db.commit()
    await db.refresh(db_project)
    return db_project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_DELETE))],
)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Permanently delete a project (Requires PROJECT_DELETE permission)."""
    stmt = select(models.Project).where(models.Project.id == project_id)
    result = await db.execute(stmt)
    db_project = result.scalar_one_or_none()

    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(db_project)
    await db.commit()
    return None


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
    "/{project_id}/hygienist",
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


@router.get("/{project_id}/hygienist", response_model=schemas.HygienistAssignment)
async def get_hygienist_assignment(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get the hygienist currently assigned to a project."""
    project = await _get_project_or_404(project_id, db)
    if not project.hygienist_link:
        raise HTTPException(
            status_code=404, detail="No hygienist assigned to this project"
        )
    return project.hygienist_link


@router.delete(
    "/{project_id}/hygienist",
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
