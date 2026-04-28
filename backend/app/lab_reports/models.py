from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.requirements import DismissibleMixin
from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.lab_results.models import SampleBatch


class LabReportRequirement(Base, AuditMixin, DismissibleMixin):
    __tablename__ = "lab_report_requirements"

    requirement_type: ClassVar[str] = "lab_report"
    is_dismissable: ClassVar[bool] = True

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sample_batch_id: Mapped[int] = mapped_column(
        ForeignKey("sample_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_saved: Mapped[bool] = mapped_column(default=False, nullable=False)
    saved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sample_batch: Mapped["SampleBatch"] = relationship("SampleBatch", lazy="selectin")

    __table_args__ = (
        # One live requirement per batch; dismissed rows don't block re-materialization.
        Index(
            "ix_uq_lab_report_active",
            "sample_batch_id",
            unique=True,
            sqlite_where=text("dismissed_at IS NULL"),
        ),
        Index("ix_lab_report_status", "project_id", "is_saved", "dismissed_at"),
    )

    @property
    def label(self) -> str:
        if self.sample_batch is not None:
            return self.sample_batch.batch_num
        return f"Batch #{self.sample_batch_id}"

    @property
    def is_dismissed(self) -> bool:
        return self.dismissed_at is not None

    @property
    def is_fulfilled(self) -> bool:
        return self.is_saved
