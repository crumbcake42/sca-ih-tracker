from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)

    # Polymorphic identifiers
    # No ForeignKey here because this ID could point to Schools, Projects, or LabResults
    parent_type: Mapped[str] = mapped_column(String(50))
    parent_id: Mapped[int] = mapped_column()

    # Native dict for 3.11+ (requires a JSON-capable column if using Postgres,
    # but for SQLite, we'll keep it simple or use a custom TypeDecorator)
    # For now, let's stick to the core fields to keep it stable.
    author: Mapped[str | None] = mapped_column(String(100))
