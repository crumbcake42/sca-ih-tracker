from datetime import datetime
from typing import ClassVar

from sqlalchemy import ForeignKey, Index, Integer, Text, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import CPRStageStatus
from app.database import AuditMixin, Base
from app.common.requirements import DismissibleMixin, ManualTerminalMixin


class ContractorPaymentRecord(Base, AuditMixin, DismissibleMixin, ManualTerminalMixin):
    __tablename__ = "contractor_payment_records"

    # Protocol class-level identifiers
    requirement_type: ClassVar[str] = "contractor_payment_record"
    is_dismissable: ClassVar[bool] = True

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contractor_id: Mapped[int] = mapped_column(
        ForeignKey("contractors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    is_required: Mapped[bool] = mapped_column(default=True, nullable=False)

    # RFA sub-flow
    rfa_submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rfa_internal_status: Mapped[CPRStageStatus | None] = mapped_column(
        SQLEnum(CPRStageStatus), nullable=True
    )
    rfa_internal_resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rfa_sca_status: Mapped[CPRStageStatus | None] = mapped_column(
        SQLEnum(CPRStageStatus), nullable=True
    )
    rfa_sca_resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # RFP sub-flow
    rfp_submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rfp_internal_status: Mapped[CPRStageStatus | None] = mapped_column(
        SQLEnum(CPRStageStatus), nullable=True
    )
    rfp_internal_resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Fulfillment signal — rfp_saved_at IS NOT NULL means fulfilled.
    rfp_saved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    contractor: Mapped["Contractor"] = relationship("Contractor", lazy="selectin")

    __table_args__ = (
        # One live CPR per (project, contractor); dismissed rows don't block re-materialization.
        Index(
            "ix_uq_cpr_active",
            "project_id",
            "contractor_id",
            unique=True,
            sqlite_where=text("dismissed_at IS NULL"),
        ),
        Index("ix_cpr_status", "project_id", "rfp_saved_at", "dismissed_at"),
    )

    @property
    def requirement_key(self) -> str:
        return str(self.contractor_id)

    @property
    def label(self) -> str:
        if self.contractor is not None:
            return f"CPR — {self.contractor.name}"
        return f"CPR — Contractor #{self.contractor_id}"

    @property
    def is_dismissed(self) -> bool:
        return self.dismissed_at is not None

    def is_fulfilled(self) -> bool:
        return self.rfp_saved_at is not None
