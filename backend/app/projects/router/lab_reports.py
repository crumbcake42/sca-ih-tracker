from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.lab_reports.models import LabReportRequirement
from app.lab_reports.schemas import LabReportRequirementRead
from app.projects.models import Project
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter(prefix="/{project_id}/lab-reports", tags=["Lab Reports"])


@router.get("/", response_model=list[LabReportRequirementRead])
async def list_lab_reports(
    project_id: int,
    include_dismissed: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(LabReportRequirement).where(
        LabReportRequirement.project_id == project_id
    )
    if not include_dismissed:
        stmt = stmt.where(LabReportRequirement.dismissed_at.is_(None))

    result = await db.execute(stmt)
    return result.scalars().all()
