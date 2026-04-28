from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cprs.models import ContractorPaymentRecord
from app.cprs.schemas import (
    ContractorPaymentRecordDismiss,
    ContractorPaymentRecordRead,
    ContractorPaymentRecordUpdate,
)
from app.cprs.service import record_stage_history_note
from app.database import get_db
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

# Routes scoped to a single CPR row: PATCH, dismiss, DELETE
# Project-scoped list/create endpoints live in app/projects/router/cprs.py
cpr_router = APIRouter(prefix="/cprs", tags=["CPRs"])


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


@cpr_router.post(
    "/{cpr_id}/undismiss",
    response_model=ContractorPaymentRecordRead,
)
async def undismiss_contractor_payment_record(
    cpr_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    record = await db.get(ContractorPaymentRecord, cpr_id)
    if not record:
        raise HTTPException(status_code=404, detail="Contractor payment record not found")
    if record.dismissed_at is None:
        raise HTTPException(status_code=422, detail="Record is not dismissed")

    collision = (
        await db.execute(
            select(ContractorPaymentRecord).where(
                ContractorPaymentRecord.project_id == record.project_id,
                ContractorPaymentRecord.contractor_id == record.contractor_id,
                ContractorPaymentRecord.dismissed_at.is_(None),
                ContractorPaymentRecord.id != record.id,
            )
        )
    ).scalar_one_or_none()
    if collision:
        raise HTTPException(
            status_code=409,
            detail="A live CPR already exists for this project and contractor",
        )

    record.dismissed_at = None
    record.dismissed_by_id = None
    record.dismissal_reason = None
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
