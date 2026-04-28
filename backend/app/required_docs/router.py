from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.required_docs.models import ProjectDocumentRequirement
from app.required_docs.schemas import (
    ProjectDocumentRequirementDismiss,
    ProjectDocumentRequirementRead,
    ProjectDocumentRequirementUpdate,
)
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

# Routes scoped to a single requirement row: PATCH, dismiss, DELETE
# Project-scoped list/create endpoints live in app/projects/router/required_docs.py
doc_req_router = APIRouter(prefix="/document-requirements", tags=["document-requirements"])


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


@doc_req_router.post(
    "/{req_id}/undismiss",
    response_model=ProjectDocumentRequirementRead,
)
async def undismiss_document_requirement(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    req = await db.get(ProjectDocumentRequirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Document requirement not found")
    if req.dismissed_at is None:
        raise HTTPException(status_code=422, detail="Requirement is not dismissed")

    collision = (
        await db.execute(
            select(ProjectDocumentRequirement).where(
                ProjectDocumentRequirement.project_id == req.project_id,
                ProjectDocumentRequirement.document_type == req.document_type,
                ProjectDocumentRequirement.employee_id == req.employee_id,
                ProjectDocumentRequirement.date == req.date,
                ProjectDocumentRequirement.school_id == req.school_id,
                ProjectDocumentRequirement.dismissed_at.is_(None),
                ProjectDocumentRequirement.id != req.id,
            )
        )
    ).scalar_one_or_none()
    if collision:
        raise HTTPException(
            status_code=409,
            detail="A live document requirement already exists with the same keys",
        )

    req.dismissed_at = None
    req.dismissed_by_id = None
    req.dismissal_reason = None
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
