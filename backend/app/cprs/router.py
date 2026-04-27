from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cprs.models import ContractorPaymentRecord
from app.cprs.schemas import (
    ContractorPaymentRecordCreate,
    ContractorPaymentRecordDismiss,
    ContractorPaymentRecordRead,
    ContractorPaymentRecordUpdate,
)
from app.cprs.service import record_stage_history_note
from app.contractors.models import Contractor
from app.database import get_db
from app.projects.models import Project, ProjectContractorLink
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

# Routes scoped to a project: GET list, POST manual create
projects_cpr_router = APIRouter(prefix="/projects", tags=["contractor-payment-records"])

# Routes scoped to a single CPR row: PATCH, dismiss, DELETE
cpr_router = APIRouter(
    prefix="/contractor-payment-records", tags=["contractor-payment-records"]
)


@projects_cpr_router.get(
    "/{project_id}/contractor-payment-records",
    response_model=list[ContractorPaymentRecordRead],
)
async def list_contractor_payment_records(
    project_id: int,
    include_dismissed: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(ContractorPaymentRecord).where(
        ContractorPaymentRecord.project_id == project_id
    )
    if not include_dismissed:
        stmt = stmt.where(ContractorPaymentRecord.dismissed_at.is_(None))

    result = await db.execute(stmt)
    return result.scalars().all()


@projects_cpr_router.post(
    "/{project_id}/contractor-payment-records",
    response_model=ContractorPaymentRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_contractor_payment_record(
    project_id: int,
    body: ContractorPaymentRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Manually create a CPR row (administrative correction or missed event)."""
    if body.project_id != project_id:
        raise HTTPException(
            status_code=422, detail="project_id in body must match URL"
        )
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    contractor = await db.get(Contractor, body.contractor_id)
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    # Verify the contractor is (or was) linked to this project
    link = (
        await db.execute(
            select(ProjectContractorLink).where(
                ProjectContractorLink.project_id == project_id,
                ProjectContractorLink.contractor_id == body.contractor_id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(
            status_code=422,
            detail="Contractor is not linked to this project",
        )

    record = ContractorPaymentRecord(
        project_id=project_id,
        contractor_id=body.contractor_id,
        is_required=True,
        notes=body.notes,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@cpr_router.patch(
    "/{cpr_id}",
    response_model=ContractorPaymentRecordRead,
)
async def update_contractor_payment_record(
    cpr_id: int,
    body: ContractorPaymentRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Update CPR stage dates and statuses.

    If rfa_submitted_at or rfp_submitted_at is re-submitted (already had a value),
    a non-blocking history note captures the prior dates before they are overwritten.
    """
    record = await db.get(ContractorPaymentRecord, cpr_id)
    if not record:
        raise HTTPException(status_code=404, detail="Contractor payment record not found")

    updates = body.model_dump(exclude_unset=True)

    if "rfa_submitted_at" in updates and record.rfa_submitted_at is not None:
        await record_stage_history_note(record, "RFA", db)
    if "rfp_submitted_at" in updates and record.rfp_submitted_at is not None:
        await record_stage_history_note(record, "RFP", db)

    for field, value in updates.items():
        setattr(record, field, value)
    record.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(record)
    return record


@cpr_router.post(
    "/{cpr_id}/dismiss",
    response_model=ContractorPaymentRecordRead,
)
async def dismiss_contractor_payment_record(
    cpr_id: int,
    body: ContractorPaymentRecordDismiss,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    record = await db.get(ContractorPaymentRecord, cpr_id)
    if not record:
        raise HTTPException(status_code=404, detail="Contractor payment record not found")
    if record.dismissed_at is not None:
        raise HTTPException(status_code=422, detail="Record is already dismissed")
    if not record.is_dismissable:
        raise HTTPException(
            status_code=422, detail="This requirement type cannot be dismissed"
        )

    record.dismissal_reason = body.dismissal_reason
    record.dismissed_by_id = current_user.id
    record.dismissed_at = datetime.now(UTC).replace(tzinfo=None)
    record.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(record)
    return record


@cpr_router.delete(
    "/{cpr_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contractor_payment_record(
    cpr_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Only pristine rows (no RFA submitted, no RFP submitted) may be deleted.
    For progressed rows, use the dismiss endpoint instead."""
    record = await db.get(ContractorPaymentRecord, cpr_id)
    if not record:
        raise HTTPException(status_code=404, detail="Contractor payment record not found")
    if record.rfa_submitted_at is not None or record.rfp_submitted_at is not None:
        raise HTTPException(
            status_code=422,
            detail="Only pristine records (no RFA/RFP submitted) may be deleted. Use the dismiss endpoint instead.",
        )

    await db.delete(record)
    await db.commit()
