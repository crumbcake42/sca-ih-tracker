from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import NoteEntityType, NoteType


class NoteCreate(BaseModel):
    """User-authored top-level note on an entity."""

    body: str = Field(min_length=1)
    is_blocking: bool = False


class NoteReply(BaseModel):
    """Reply to an existing top-level note. Replies are never blocking."""

    body: str = Field(min_length=1)


class NoteResolve(BaseModel):
    """Body payload for PATCH /notes/{id}/resolve. Resolution note is
    auto-appended as a reply to preserve rationale."""

    resolution_note: str = Field(min_length=1)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: NoteEntityType
    entity_id: int
    parent_note_id: int | None
    body: str
    note_type: NoteType | None
    is_blocking: bool
    is_resolved: bool
    resolved_by_id: int | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by_id: int | None
    updated_by_id: int | None
    replies: list["NoteRead"] = []


NoteRead.model_rebuild()
