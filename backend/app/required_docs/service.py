from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.config import SYSTEM_USER_ID
from app.common.enums import DocumentType, EmployeeRoleType, RequirementEvent
from app.requirement_triggers.models import WACodeRequirementTrigger
from app.common.requirements import register_requirement_type
from app.required_docs.models import ProjectDocumentRequirement
from app.time_entries.models import TimeEntry

# Maps employee role types to the document types that a time entry of that role triggers.
# Adding a role here requires no migration — it is a code-only change.
ROLES_REQUIRING_DAILY_LOG: dict[EmployeeRoleType, list[DocumentType]] = {
    EmployeeRoleType.ACM_AIR_TECH: [DocumentType.DAILY_LOG],
    EmployeeRoleType.ACM_PROJECT_MONITOR: [DocumentType.DAILY_LOG],
}


async def materialize_for_time_entry(
    project_id: int, time_entry_id: int, db: AsyncSession
) -> None:
    """Create DAILY_LOG rows for each document type the time entry's role requires.

    Idempotent: skips if a non-dismissed row already exists for the same
    (project, document_type, employee, date, school) tuple.
    Caller owns the transaction — no flush or commit inside.
    """
    result = await db.execute(
        select(TimeEntry)
        .where(TimeEntry.id == time_entry_id)
        .options(selectinload(TimeEntry.employee_role))
        .execution_options(populate_existing=True)
    )
    entry = result.scalar_one_or_none()
    if entry is None or entry.employee_role is None:
        return

    doc_types = ROLES_REQUIRING_DAILY_LOG.get(entry.employee_role.role_type, [])
    if not doc_types:
        return

    entry_date = entry.start_datetime.date()
    for doc_type in doc_types:
        existing = (
            await db.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project_id,
                    ProjectDocumentRequirement.document_type == doc_type,
                    ProjectDocumentRequirement.employee_id == entry.employee_id,
                    ProjectDocumentRequirement.date == entry_date,
                    ProjectDocumentRequirement.school_id == entry.school_id,
                    ProjectDocumentRequirement.dismissed_at.is_(None),
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            db.add(
                ProjectDocumentRequirement(
                    project_id=project_id,
                    document_type=doc_type,
                    is_required=True,
                    is_saved=False,
                    is_placeholder=False,
                    employee_id=entry.employee_id,
                    date=entry_date,
                    school_id=entry.school_id,
                    expected_role_type=entry.employee_role.role_type,
                    created_by_id=SYSTEM_USER_ID,
                )
            )


async def materialize_for_wa_code_added(
    project_id: int, wa_code_id: int, db: AsyncSession
) -> None:
    """Create document requirement rows for each wa_code_requirement_trigger associated with
    the added WA code that specifies a project_document document_type.

    Idempotent: skips if a non-dismissed row already exists for the same trigger.
    Caller owns the transaction.
    """
    triggers = (
        await db.execute(
            select(WACodeRequirementTrigger).where(
                WACodeRequirementTrigger.wa_code_id == wa_code_id,
                WACodeRequirementTrigger.requirement_type_name == "project_document",
            )
        )
    ).scalars().all()

    for trigger in triggers:
        doc_type_str = trigger.template_params.get("document_type")
        if not doc_type_str:
            continue
        try:
            doc_type = DocumentType(doc_type_str)
        except ValueError:
            continue

        existing = (
            await db.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project_id,
                    ProjectDocumentRequirement.wa_code_trigger_id == trigger.id,
                    ProjectDocumentRequirement.dismissed_at.is_(None),
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            db.add(
                ProjectDocumentRequirement(
                    project_id=project_id,
                    document_type=doc_type,
                    is_required=True,
                    is_saved=False,
                    is_placeholder=False,
                    wa_code_trigger_id=trigger.id,
                    created_by_id=SYSTEM_USER_ID,
                )
            )


async def cleanup_for_wa_code_removed(
    project_id: int, wa_code_id: int, db: AsyncSession
) -> None:
    """Remove pristine rows that were materialized by triggers for the removed WA code.

    Decision #6: a row is pristine if is_saved=False, dismissed_at IS NULL, and file_id IS NULL.
    Progressed rows (any of those conditions true) are left in place so managers can
    inspect and manually dismiss them.
    Caller owns the transaction.
    """
    triggers = (
        await db.execute(
            select(WACodeRequirementTrigger).where(
                WACodeRequirementTrigger.wa_code_id == wa_code_id,
                WACodeRequirementTrigger.requirement_type_name == "project_document",
            )
        )
    ).scalars().all()

    if not triggers:
        return

    trigger_ids = [t.id for t in triggers]
    rows = (
        await db.execute(
            select(ProjectDocumentRequirement).where(
                ProjectDocumentRequirement.project_id == project_id,
                ProjectDocumentRequirement.wa_code_trigger_id.in_(trigger_ids),
            )
        )
    ).scalars().all()

    for row in rows:
        if not row.is_saved and row.dismissed_at is None and row.file_id is None:
            await db.delete(row)


@register_requirement_type(
    "project_document",
    events=[
        RequirementEvent.TIME_ENTRY_CREATED,
        RequirementEvent.WA_CODE_ADDED,
        RequirementEvent.WA_CODE_REMOVED,
    ],
)
class ProjectDocumentHandler:
    """Registry handler for Silo 1 document requirements.

    Not an ORM model — delegates DB operations to the materializer functions above.
    get_unfulfilled_for_project returns ProjectDocumentRequirement instances,
    which satisfy the ProjectRequirement protocol structurally.
    """

    requirement_type: ClassVar[str] = "project_document"
    is_dismissable: ClassVar[bool] = True

    @classmethod
    async def handle_event(
        cls, project_id: int, event: RequirementEvent, payload: dict, db: AsyncSession
    ) -> None:
        if event == RequirementEvent.TIME_ENTRY_CREATED:
            await materialize_for_time_entry(project_id, payload["time_entry_id"], db)
        elif event == RequirementEvent.WA_CODE_ADDED:
            await materialize_for_wa_code_added(project_id, payload["wa_code_id"], db)
        elif event == RequirementEvent.WA_CODE_REMOVED:
            await cleanup_for_wa_code_removed(project_id, payload["wa_code_id"], db)

    @classmethod
    async def get_unfulfilled_for_project(
        cls, project_id: int, db: AsyncSession
    ) -> list[ProjectDocumentRequirement]:
        return list(
            (
                await db.execute(
                    select(ProjectDocumentRequirement).where(
                        ProjectDocumentRequirement.project_id == project_id,
                        ProjectDocumentRequirement.is_required.is_(True),
                        ProjectDocumentRequirement.is_saved.is_(False),
                        ProjectDocumentRequirement.dismissed_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
