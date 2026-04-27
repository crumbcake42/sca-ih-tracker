from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import NoteEntityType, NoteType, RequirementEvent
from app.cprs.models import ContractorPaymentRecord
from app.common.requirements import register_requirement_type


async def materialize_for_contractor_linked(
    project_id: int, contractor_id: int, db: AsyncSession
) -> None:
    """Create a CPR row for the (project, contractor) pair if one does not already exist.

    Idempotent: skips if a non-dismissed row already exists.
    Caller owns the transaction — no flush or commit inside.
    """
    existing = (
        await db.execute(
            select(ContractorPaymentRecord).where(
                ContractorPaymentRecord.project_id == project_id,
                ContractorPaymentRecord.contractor_id == contractor_id,
                ContractorPaymentRecord.dismissed_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            ContractorPaymentRecord(
                project_id=project_id,
                contractor_id=contractor_id,
                is_required=True,
                created_by_id=SYSTEM_USER_ID,
                updated_by_id=SYSTEM_USER_ID,
            )
        )


async def cleanup_for_contractor_unlinked(
    project_id: int, contractor_id: int, db: AsyncSession
) -> None:
    """Remove pristine CPR rows when a contractor is unlinked from a project.

    Decision #6: a row is pristine if rfa_submitted_at IS NULL, dismissed_at IS NULL,
    and file_id IS NULL. Progressed rows are left so managers can inspect and dismiss.
    Caller owns the transaction.
    """
    rows = (
        await db.execute(
            select(ContractorPaymentRecord).where(
                ContractorPaymentRecord.project_id == project_id,
                ContractorPaymentRecord.contractor_id == contractor_id,
            )
        )
    ).scalars().all()

    for row in rows:
        if (
            row.rfa_submitted_at is None
            and row.dismissed_at is None
            and row.file_id is None
        ):
            await db.delete(row)


async def record_stage_history_note(
    record: ContractorPaymentRecord, stage: str, db: AsyncSession
) -> None:
    """Capture prior stage dates as a history note before they are overwritten on re-submission.

    Creates a non-blocking, immediately-resolved system note attached to the CPR row.
    This note serves as an audit trail only — it does not gate project closure.
    """
    from app.notes.models import Note

    body_parts: list[str] = []
    if stage == "RFA":
        if record.rfa_submitted_at:
            body_parts.append(f"rfa_submitted_at: {record.rfa_submitted_at.isoformat()}")
        if record.rfa_internal_status:
            body_parts.append(f"rfa_internal_status: {record.rfa_internal_status}")
        if record.rfa_internal_resolved_at:
            body_parts.append(
                f"rfa_internal_resolved_at: {record.rfa_internal_resolved_at.isoformat()}"
            )
        if record.rfa_sca_status:
            body_parts.append(f"rfa_sca_status: {record.rfa_sca_status}")
        if record.rfa_sca_resolved_at:
            body_parts.append(
                f"rfa_sca_resolved_at: {record.rfa_sca_resolved_at.isoformat()}"
            )
    else:  # RFP
        if record.rfp_submitted_at:
            body_parts.append(f"rfp_submitted_at: {record.rfp_submitted_at.isoformat()}")
        if record.rfp_internal_status:
            body_parts.append(f"rfp_internal_status: {record.rfp_internal_status}")
        if record.rfp_internal_resolved_at:
            body_parts.append(
                f"rfp_internal_resolved_at: {record.rfp_internal_resolved_at.isoformat()}"
            )

    prior_summary = "; ".join(body_parts) if body_parts else "none"
    note = Note(
        entity_type=NoteEntityType.CONTRACTOR_PAYMENT_RECORD,
        entity_id=record.id,
        note_type=NoteType.CPR_STAGE_REGRESSION,
        body=f"{stage} re-submission. Prior values: {prior_summary}",
        is_blocking=False,
        is_resolved=True,  # History record only — resolved immediately
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(note)
    await db.flush()


@register_requirement_type(
    "contractor_payment_record",
    events=[
        RequirementEvent.CONTRACTOR_LINKED,
        RequirementEvent.CONTRACTOR_UNLINKED,
    ],
)
class ContractorPaymentRecordHandler:
    """Registry handler for Silo 2 contractor payment records.

    Not an ORM model — delegates DB operations to the materializer functions above.
    get_unfulfilled_for_project returns ContractorPaymentRecord instances,
    which satisfy the ProjectRequirement protocol structurally.
    """

    requirement_type: ClassVar[str] = "contractor_payment_record"
    is_dismissable: ClassVar[bool] = True
    has_manual_terminals: ClassVar[bool] = True

    @classmethod
    async def handle_event(
        cls, project_id: int, event: RequirementEvent, payload: dict, db: AsyncSession
    ) -> None:
        if event == RequirementEvent.CONTRACTOR_LINKED:
            await materialize_for_contractor_linked(
                project_id, payload["contractor_id"], db
            )
        elif event == RequirementEvent.CONTRACTOR_UNLINKED:
            await cleanup_for_contractor_unlinked(
                project_id, payload["contractor_id"], db
            )

    @classmethod
    async def get_unfulfilled_for_project(
        cls, project_id: int, db: AsyncSession
    ) -> list[ContractorPaymentRecord]:
        return list(
            (
                await db.execute(
                    select(ContractorPaymentRecord).where(
                        ContractorPaymentRecord.project_id == project_id,
                        ContractorPaymentRecord.is_required.is_(True),
                        ContractorPaymentRecord.rfp_saved_at.is_(None),
                        ContractorPaymentRecord.dismissed_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
