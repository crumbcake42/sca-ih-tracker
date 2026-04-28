from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import DocumentType
from app.database import get_db
from app.projects.models import Project
from app.required_docs.models import ProjectDocumentRequirement
from app.required_docs.schemas import (
    ProjectDocumentRequirementCreate,
    ProjectDocumentRequirementRead,
)
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter(prefix="/{project_id}/document-requirements", tags=["document-requirements"])


@router.get("/", response_model=list[ProjectDocumentRequirementRead])
async def list_document_requirements(
    project_id: int,
    document_type: DocumentType | None = Query(None),
    include_dismissed: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(ProjectDocumentRequirement).where(
        ProjectDocumentRequirement.project_id == project_id
    )
    if document_type is not None:
        stmt = stmt.where(ProjectDocumentRequirement.document_type == document_type)
    if not include_dismissed:
        stmt = stmt.where(ProjectDocumentRequirement.dismissed_at.is_(None))

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/",
    response_model=ProjectDocumentRequirementRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_requirement(
    project_id: int,
    body: ProjectDocumentRequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Manually create a requirement row (e.g. re-occupancy letter, minor letter)."""
    if body.project_id != project_id:
        raise HTTPException(status_code=422, detail="project_id in body must match URL")
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    req = ProjectDocumentRequirement(
        project_id=project_id,
        document_type=body.document_type,
        is_required=True,
        is_saved=False,
        is_placeholder=body.is_placeholder,
        employee_id=body.employee_id,
        date=body.date,
        school_id=body.school_id,
        expected_role_type=body.expected_role_type,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req
