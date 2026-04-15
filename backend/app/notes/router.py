from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums import NoteEntityType
from app.database import get_db
from app.notes.models import Note
from app.notes.schemas import NoteCreate, NoteRead, NoteReply, NoteResolve
from app.notes.service import validate_entity_exists
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/{entity_type}/{entity_id}", response_model=list[NoteRead])
async def list_notes(
    entity_type: NoteEntityType,
    entity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """All top-level notes on an entity, ordered by created_at. Replies are nested."""
    result = await db.execute(
        select(Note)
        .where(
            Note.entity_type == entity_type,
            Note.entity_id == entity_id,
            Note.parent_note_id.is_(None),
        )
        .options(selectinload(Note.replies).selectinload(Note.replies))
        .order_by(Note.created_at)
        .execution_options(populate_existing=True)
    )
    return result.scalars().all()


# NOTE: the reply route is registered BEFORE the generic /{entity_type}/{entity_id}
# POST route. Starlette matches routes in registration order. For a path like
# /notes/42/reply, /{note_id}/reply is more specific (literal "reply" segment)
# but Starlette doesn't auto-prioritise literals — the more-specific route must
# come first. For /notes/project/42, /{note_id}/reply does NOT structurally match
# (second segment is "42" not "reply"), so Starlette falls through to the next POST.


@router.post(
    "/{note_id}/reply",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reply(
    note_id: int,
    body: NoteReply,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """
    Add a reply to a top-level note. Only one level of nesting is allowed —
    replying to a reply is rejected with 422.
    """
    parent = await db.get(Note, note_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Note not found")
    if parent.parent_note_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Cannot reply to a reply — only one level of nesting is allowed",
        )

    reply = Note(
        entity_type=parent.entity_type,
        entity_id=parent.entity_id,
        parent_note_id=parent.id,
        body=body.body,
        is_blocking=False,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(reply)
    await db.commit()

    # Expunge the reply so the reload below gets a fresh Python object.
    # A just-created Note has `replies` in an uninitialised state; if it stays
    # in the identity map the nested selectinload will think the collection is
    # "already present" and skip the secondary query, leaving reply.replies in
    # a lazy state that raises MissingGreenlet during serialisation.
    reply_id = reply.id
    db.expunge(reply)
    result = await db.execute(
        select(Note)
        .where(Note.id == reply_id)
        .options(selectinload(Note.replies).selectinload(Note.replies))
    )
    return result.scalar_one()


@router.post(
    "/{entity_type}/{entity_id}",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    entity_type: NoteEntityType,
    entity_id: int,
    body: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Create a user note on an entity. Validates the entity exists first."""
    await validate_entity_exists(entity_type, entity_id, db)

    note = Note(
        entity_type=entity_type,
        entity_id=entity_id,
        body=body.body,
        is_blocking=body.is_blocking,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(note)
    await db.commit()

    # Same identity-map / selectinload reasoning as create_reply above.
    note_id = note.id
    db.expunge(note)
    result = await db.execute(
        select(Note)
        .where(Note.id == note_id)
        .options(selectinload(Note.replies).selectinload(Note.replies))
    )
    return result.scalar_one()


@router.patch("/{note_id}/resolve", response_model=NoteRead)
async def resolve_note(
    note_id: int,
    body: NoteResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """
    Resolve a user-authored blocking note.

    System notes (note_type IS NOT NULL) cannot be manually resolved — they
    auto-resolve when the underlying condition clears.

    The resolution_note is appended as a reply to preserve the rationale.
    """
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.note_type is not None:
        raise HTTPException(
            status_code=422,
            detail="System notes cannot be manually resolved — they resolve automatically when the condition clears",
        )
    if note.is_resolved:
        raise HTTPException(status_code=422, detail="Note is already resolved")

    now = datetime.now(tz=UTC)
    note.is_resolved = True
    note.resolved_by_id = current_user.id
    note.resolved_at = now
    note.updated_by_id = current_user.id

    # Preserve resolution rationale as a reply
    resolution_reply = Note(
        entity_type=note.entity_type,
        entity_id=note.entity_id,
        parent_note_id=note.id,
        body=body.resolution_note,
        is_blocking=False,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(resolution_reply)
    await db.commit()

    # Expunge both the parent note and the resolution reply so the reload below
    # gets fresh Python objects. A just-created Note object has `replies` in an
    # uninitialised state; if it remains in the identity map the nested
    # selectinload sees the collection as "already present" and skips the
    # secondary query, leaving reply.replies lazy → MissingGreenlet on serialise.
    parent_note_id = note.id
    db.expunge(note)
    db.expunge(resolution_reply)
    result = await db.execute(
        select(Note)
        .where(Note.id == parent_note_id)
        .options(selectinload(Note.replies).selectinload(Note.replies))
    )
    return result.scalar_one()
