from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import DocumentType
from app.database import get_db
from app.projects.models import Project
from app.required_docs.models import ProjectDocumentRequirement
from app.required_docs.schemas import (
    ProjectDocumentRequirementCreate,
    ProjectDocumentRequirementDismiss,
    ProjectDocumentRequirementRead,
    ProjectDocumentRequirementUpdate,
)
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

# Routes scoped to a project: GET list, POST manual create
projects_doc_router = APIRouter(prefix="/projects", tags=["document-requirements"])

# Routes scoped to a single requirement row: PATCH, dismiss, DELETE
doc_req_router = APIRouter(prefix="/document-requirements", tags=["document-requirements"])


@projects_doc_router.get(
    "/{project_id}/document-requirements",
    response_model=list[ProjectDocumentRequirementRead],
)
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


@projects_doc_router.post(
    "/{project_id}/document-requirements",
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
        raise HTTPException(
            status_code=422, detail="project_id in body must match URL"
        )
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


@doc_req_router.patch(
    "/{req_id}",
    response_model=ProjectDocumentRequirementRead,
)
async def update_document_requirement(
    req_id: int,
    body: ProjectDocumentRequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    req = await db.get(ProjectDocumentRequirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Document requirement not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(req, field, value)
    req.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(req)
    return req


@doc_req_router.post(
    "/{req_id}/dismiss",
    response_model=ProjectDocumentRequirementRead,
)
async def dismiss_document_requirement(
    req_id: int,
    body: ProjectDocumentRequirementDismiss,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    req = await db.get(ProjectDocumentRequirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Document requirement not found")
    if req.dismissed_at is not None:
        raise HTTPException(status_code=422, detail="Requirement is already dismissed")
    if not req.is_dismissable:
        raise HTTPException(status_code=422, detail="This requirement type cannot be dismissed")

    req.dismissal_reason = body.dismissal_reason
    req.dismissed_by_id = current_user.id
    req.dismissed_at = datetime.now(UTC).replace(tzinfo=None)
    req.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(req)
    return req


@doc_req_router.delete(
    "/{req_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document_requirement(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Only placeholder rows that have not been saved may be deleted.
    For all other rows, use the dismiss endpoint instead."""
    req = await db.get(ProjectDocumentRequirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Document requirement not found")
    if not req.is_placeholder or req.is_saved:
        raise HTTPException(
            status_code=422,
            detail="Only unsaved placeholder rows may be deleted. Use the dismiss endpoint instead.",
        )

    await db.delete(req)
    await db.commit()
