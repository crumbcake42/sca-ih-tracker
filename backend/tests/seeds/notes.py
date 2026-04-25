from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import NoteEntityType, NoteType
from app.notes.models import Note


async def seed_note(
    db: AsyncSession,
    entity_type: NoteEntityType,
    entity_id: int,
    body: str = "Test note",
    *,
    is_blocking: bool = False,
    note_type: NoteType | None = None,
    parent_note_id: int | None = None,
    resolved: bool = False,
) -> Note:
    note = Note(
        entity_type=entity_type,
        entity_id=entity_id,
        body=body,
        is_blocking=is_blocking,
        note_type=note_type,
        parent_note_id=parent_note_id,
        is_resolved=resolved,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    if resolved:
        note.resolved_by_id = SYSTEM_USER_ID
        note.resolved_at = datetime.now(tz=UTC)
    db.add(note)
    await db.flush()
    return note


async def seed_blocking_note(
    db: AsyncSession,
    *,
    body: str = "Blocking issue",
    entity_type: NoteEntityType,
    entity_id: int,
    is_resolved: bool = False,
) -> Note:
    note = Note(
        entity_type=entity_type,
        entity_id=entity_id,
        body=body,
        is_blocking=True,
        is_resolved=is_resolved,
        created_by_id=1,
        updated_by_id=1,
    )
    db.add(note)
    await db.flush()
    return note
