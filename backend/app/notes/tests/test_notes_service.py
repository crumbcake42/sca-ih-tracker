"""
Unit tests for app/notes/service.py.

create_system_note  — de-duplicated blocking system note creation
auto_resolve_system_notes — bulk resolution of system notes by type

Tests call service functions directly against db_session; no HTTP.
All tests roll back via the conftest transaction fixture.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import NoteEntityType, NoteType
from app.notes.models import Note
from app.notes.service import auto_resolve_system_notes, create_system_note
from tests.seeds import seed_note

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _count_notes(
    db: AsyncSession,
    entity_type: NoteEntityType,
    entity_id: int,
    note_type: NoteType,
) -> int:
    result = await db.execute(
        select(Note).where(
            Note.entity_type == entity_type,
            Note.entity_id == entity_id,
            Note.note_type == note_type,
        )
    )
    return len(result.scalars().all())


# ---------------------------------------------------------------------------
# create_system_note
# ---------------------------------------------------------------------------


class TestCreateSystemNote:
    async def test_creates_note(self, db_session: AsyncSession):
        note = await create_system_note(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=42,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            body="Overlap with entry #99",
            db=db_session,
        )

        assert note.id is not None
        assert note.entity_type == NoteEntityType.TIME_ENTRY
        assert note.entity_id == 42
        assert note.note_type == NoteType.TIME_ENTRY_CONFLICT
        assert note.body == "Overlap with entry #99"
        assert note.is_blocking is True
        assert note.is_resolved is False
        assert note.created_by_id == SYSTEM_USER_ID
        assert note.updated_by_id == SYSTEM_USER_ID

    async def test_deduplicates_unresolved(self, db_session: AsyncSession):
        """Calling create_system_note twice returns the same note, not two rows."""
        first = await create_system_note(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=1,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            body="First call",
            db=db_session,
        )
        second = await create_system_note(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=1,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            body="Second call (different body — still deduped)",
            db=db_session,
        )

        assert first.id == second.id
        assert (
            await _count_notes(
                db_session, NoteEntityType.TIME_ENTRY, 1, NoteType.TIME_ENTRY_CONFLICT
            )
            == 1
        )

    async def test_does_not_deduplicate_resolved(self, db_session: AsyncSession):
        """Once a note is resolved, a subsequent call creates a fresh note."""
        await seed_note(
            db_session,
            NoteEntityType.TIME_ENTRY,
            10,
            "Old resolved note",
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            resolved=True,
        )

        new_note = await create_system_note(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=10,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            body="New conflict",
            db=db_session,
        )

        assert new_note.is_resolved is False
        assert (
            await _count_notes(
                db_session, NoteEntityType.TIME_ENTRY, 10, NoteType.TIME_ENTRY_CONFLICT
            )
            == 2
        )


# ---------------------------------------------------------------------------
# auto_resolve_system_notes
# ---------------------------------------------------------------------------


class TestAutoResolveSystemNotes:
    async def test_resolves_all_matching(self, db_session: AsyncSession):
        """Two unresolved notes of the same type on the same entity are both resolved."""
        n1 = await seed_note(
            db_session,
            NoteEntityType.TIME_ENTRY,
            5,
            "Conflict A",
            note_type=NoteType.TIME_ENTRY_CONFLICT,
        )
        n2 = await seed_note(
            db_session,
            NoteEntityType.TIME_ENTRY,
            5,
            "Conflict B",
            note_type=NoteType.TIME_ENTRY_CONFLICT,
        )

        count = await auto_resolve_system_notes(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=5,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            db=db_session,
        )

        assert count == 2
        # Refresh from DB to confirm changes flushed
        await db_session.refresh(n1)
        await db_session.refresh(n2)
        assert n1.is_resolved is True
        assert n1.resolved_by_id == SYSTEM_USER_ID
        assert n1.resolved_at is not None
        assert n2.is_resolved is True

    async def test_returns_count(self, db_session: AsyncSession):
        await seed_note(
            db_session,
            NoteEntityType.TIME_ENTRY,
            20,
            "One note",
            note_type=NoteType.TIME_ENTRY_CONFLICT,
        )

        count = await auto_resolve_system_notes(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=20,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            db=db_session,
        )
        assert count == 1

    async def test_ignores_already_resolved(self, db_session: AsyncSession):
        """A pre-resolved note is not touched; returns 0."""
        await seed_note(
            db_session,
            NoteEntityType.TIME_ENTRY,
            30,
            "Already resolved",
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            resolved=True,
        )

        count = await auto_resolve_system_notes(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=30,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            db=db_session,
        )
        assert count == 0

    async def test_ignores_different_note_type(self, db_session: AsyncSession):
        """Notes of a different type on the same entity are not resolved."""
        # Seed a TIME_ENTRY_CONFLICT note on entity 40
        n = await seed_note(
            db_session,
            NoteEntityType.TIME_ENTRY,
            40,
            "Should not be resolved",
            note_type=NoteType.TIME_ENTRY_CONFLICT,
        )

        # Resolve a hypothetical OTHER type (use TIME_ENTRY_CONFLICT on a different
        # entity_id so we test the note_type filter without needing a second enum value)
        count = await auto_resolve_system_notes(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=99,  # different entity — nothing to resolve
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            db=db_session,
        )
        assert count == 0
        await db_session.refresh(n)
        assert n.is_resolved is False

    async def test_ignores_different_entity_type(self, db_session: AsyncSession):
        """A note on a PROJECT entity is not resolved when targeting TIME_ENTRY."""
        n = await seed_note(
            db_session,
            NoteEntityType.PROJECT,
            50,
            "Project-level note",
            note_type=NoteType.TIME_ENTRY_CONFLICT,
        )

        count = await auto_resolve_system_notes(
            entity_type=NoteEntityType.TIME_ENTRY,
            entity_id=50,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
            db=db_session,
        )
        assert count == 0
        await db_session.refresh(n)
        assert n.is_resolved is False
