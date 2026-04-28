from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.lab_reports.models import LabReportRequirement
from app.lab_reports.schemas import (
    LabReportRequirementDismiss,
    LabReportRequirementRead,
    LabReportRequirementUpdate,
)
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

lab_report_router = APIRouter(prefix="/lab-reports", tags=["Lab Reports"])

_edit_dep = PermissionChecker(PermissionName.PROJECT_EDIT)


@lab_report_router.patch("/{req_id}/save", response_model=LabReportRequirementRead)
async def save_lab_report(
    req_id: int,
    body: LabReportRequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit_dep),
):
    req = await db.get(LabReportRequirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Lab report requirement not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(req, field, value)

    if updates.get("is_saved") is True and req.saved_at is None:
        req.saved_at = datetime.now(UTC).replace(tzinfo=None)

    req.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(req)
    return req


@lab_report_router.post("/{req_id}/dismiss", response_model=LabReportRequirementRead)
async def dismiss_lab_report(
    req_id: int,
    body: LabReportRequirementDismiss,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit_dep),
):
    req = await db.get(LabReportRequirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Lab report requirement not found")
    if req.dismissed_at is not None:
        raise HTTPException(status_code=422, detail="Lab report requirement is already dismissed")

    req.dismissal_reason = body.dismissal_reason
    req.dismissed_by_id = current_user.id
    req.dismissed_at = datetime.now(UTC).replace(tzinfo=None)
    req.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(req)
    return req


@lab_report_router.post("/{req_id}/undismiss", response_model=LabReportRequirementRead)
async def undismiss_lab_report(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit_dep),
):
    req = await db.get(LabReportRequirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Lab report requirement not found")
    if req.dismissed_at is None:
        raise HTTPException(status_code=422, detail="Lab report requirement is not dismissed")

    req.dismissed_at = None
    req.dismissed_by_id = None
    req.dismissal_reason = None
    req.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(req)
    return req
