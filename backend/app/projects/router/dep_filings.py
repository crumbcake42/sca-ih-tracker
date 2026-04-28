from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dep_filings.models import DEPFilingForm, ProjectDEPFiling
from app.dep_filings.schemas import ProjectDEPFilingCreate, ProjectDEPFilingRead
from app.dep_filings.service import materialize_for_form_selection
from app.projects.models import Project
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter(prefix="/{project_id}/dep-filings", tags=["DEP filings"])


@router.get("/", response_model=list[ProjectDEPFilingRead])
async def list_dep_filings(
    project_id: int,
    include_dismissed: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(ProjectDEPFiling).where(ProjectDEPFiling.project_id == project_id)
    if not include_dismissed:
        stmt = stmt.where(ProjectDEPFiling.dismissed_at.is_(None))

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/",
    response_model=list[ProjectDEPFilingRead],
    status_code=status.HTTP_201_CREATED,
)
async def select_dep_filings_for_project(
    project_id: int,
    body: ProjectDEPFilingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Manager selects which DEP filing forms apply to this project.

    Idempotent: re-POSTing with the same form_ids creates no duplicates.
    Returns the resulting live rows (both newly created and pre-existing).
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for form_id in body.form_ids:
        form = await db.get(DEPFilingForm, form_id)
        if not form:
            raise HTTPException(status_code=422, detail=f"DEP filing form {form_id} not found")

    rows = await materialize_for_form_selection(project_id, body.form_ids, current_user.id, db)
    await db.commit()

    # Reload with fresh selectin so relationship-based properties (label) serialize correctly
    refreshed = []
    for row in rows:
        await db.refresh(row)
        refreshed.append(row)
    return refreshed
