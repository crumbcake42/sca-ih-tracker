from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import NoteEntityType, NoteType
from app.database import AuditMixin, Base


class Note(Base, AuditMixin):
    __tablename__ = "notes"
    __table_args__ = (
        # Lookup by entity (e.g. all notes on a time_entry) is the hot path.
        Index("ix_notes_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Polymorphic attachment — no DB-level FK; service validates entity existence.
    entity_type: Mapped[NoteEntityType] = mapped_column(SQLEnum(NoteEntityType))
    entity_id: Mapped[int] = mapped_column()

    # One level of replies only. Enforced at service/schema layer.
    parent_note_id: Mapped[int | None] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"), nullable=True, index=True
    )

    body: Mapped[str] = mapped_column(Text)

    # NULL => user-authored; non-NULL => system-generated.
    note_type: Mapped[NoteType | None] = mapped_column(
        SQLEnum(NoteType), nullable=True
    )

    is_blocking: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    is_resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    resolved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    parent: Mapped["Note | None"] = relationship(
        "Note",
        back_populates="replies",
        remote_side="Note.id",
    )
    replies: Mapped[list["Note"]] = relationship(
        "Note",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
