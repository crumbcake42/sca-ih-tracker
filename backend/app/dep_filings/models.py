from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.requirements import DismissibleMixin
from app.database import AuditMixin, Base

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Config layer — admin-managed; adding a new form requires no migration
# ---------------------------------------------------------------------------


class DEPFilingForm(Base, AuditMixin):
    __tablename__ = "dep_filing_forms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default_selected: Mapped[bool] = mapped_column(default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(default=0, nullable=False)


# ---------------------------------------------------------------------------
# Data layer — one row per (project, form); satisfies ProjectRequirement protocol
# ---------------------------------------------------------------------------


class ProjectDEPFiling(Base, AuditMixin, DismissibleMixin):
    __tablename__ = "project_dep_filings"

    # Protocol class-level identifiers
    requirement_type: ClassVar[str] = "project_dep_filing"
    is_dismissable: ClassVar[bool] = True

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dep_filing_form_id: Mapped[int] = mapped_column(
        ForeignKey("dep_filing_forms.id"), nullable=False, index=True
    )
    is_saved: Mapped[bool] = mapped_column(default=False, nullable=False)
    saved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    form: Mapped["DEPFilingForm"] = relationship("DEPFilingForm", lazy="selectin")

    __table_args__ = (
        # One live filing per (project, form); dismissed rows don't block re-materialization.
        Index(
            "ix_uq_dep_filing_active",
            "project_id",
            "dep_filing_form_id",
            unique=True,
            sqlite_where=text("dismissed_at IS NULL"),
        ),
        Index("ix_dep_filing_status", "project_id", "is_saved", "dismissed_at"),
    )

    @property
    def label(self) -> str:
        if self.form is not None:
            return self.form.label
        return f"DEP Filing Form #{self.dep_filing_form_id}"

    @property
    def is_dismissed(self) -> bool:
        return self.dismissed_at is not None

    @property
    def is_fulfilled(self) -> bool:
        return self.is_saved
