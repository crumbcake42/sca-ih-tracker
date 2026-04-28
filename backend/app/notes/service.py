from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import NoteEntityType, NoteType
from app.notes.models import Note


async def validate_entity_exists(
    entity_type: NoteEntityType,
    entity_id: int,
    db: AsyncSession,
) -> None:
    """
    Raise 404 if entity_type + entity_id does not correspond to an existing record.

    Uses db.get() — safe here because the result is never serialized; we only
    check existence. Inline imports avoid module-level circular-import risk.
    """
    from app.cprs.models import ContractorPaymentRecord
    from app.deliverables.models import Deliverable
    from app.lab_results.models import SampleBatch
    from app.projects.models import Project
    from app.time_entries.models import TimeEntry

    model_map = {
        NoteEntityType.PROJECT: Project,
        NoteEntityType.TIME_ENTRY: TimeEntry,
        NoteEntityType.DELIVERABLE: Deliverable,
        NoteEntityType.SAMPLE_BATCH: SampleBatch,
        NoteEntityType.CONTRACTOR_PAYMENT_RECORD: ContractorPaymentRecord,
    }
    model = model_map[entity_type]
    if not await db.get(model, entity_id):
        label = entity_type.value.replace("_", " ").title()
        raise HTTPException(status_code=404, detail=f"{label} {entity_id} not found")


async def create_system_note(
    entity_type: NoteEntityType,
    entity_id: int,
    note_type: NoteType,
    body: str,
    db: AsyncSession,
) -> Note:
    """
    Insert a blocking system note with created_by_id = SYSTEM_USER_ID.

    De-duplicated: if an unresolved note with the same
    (entity_type, entity_id, note_type) already exists, return it without
    creating a second one.
    """
    existing = (
        await db.execute(
            select(Note).where(
                Note.entity_type == entity_type,
                Note.entity_id == entity_id,
                Note.note_type == note_type,
                Note.is_resolved.is_(False),
            )
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    note = Note(
        entity_type=entity_type,
        entity_id=entity_id,
        note_type=note_type,
        body=body,
        is_blocking=True,
        is_resolved=False,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(note)
    await db.flush()
    return note


async def auto_resolve_system_notes(
    entity_type: NoteEntityType,
    entity_id: int,
    note_type: NoteType,
    db: AsyncSession,
) -> int:
    """
    Resolve all unresolved system notes of a given type on a given entity.

    Sets is_resolved=True, resolved_by_id=SYSTEM_USER_ID, resolved_at=now().
    Returns the count of notes resolved (0 means nothing to clear).

    Called from service layer when the underlying condition clears
    (e.g., a time-entry overlap is corrected).
    """
    rows = (
        await db.execute(
            select(Note).where(
                Note.entity_type == entity_type,
                Note.entity_id == entity_id,
                Note.note_type == note_type,
                Note.is_resolved.is_(False),
            )
        )
    ).scalars().all()

    now = datetime.now(tz=UTC)
    for note in rows:
        note.is_resolved = True
        note.resolved_by_id = SYSTEM_USER_ID
        note.resolved_at = now
        note.updated_by_id = SYSTEM_USER_ID

    await db.flush()
    return len(rows)
