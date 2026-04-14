from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import (
    InternalDeliverableStatus,
    SCADeliverableStatus,
    WACodeLevel,
)
from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.projects.models import Project
    from app.wa_codes.models import WACode


class Deliverable(Base, AuditMixin):
    __tablename__ = "deliverables"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[WACodeLevel] = mapped_column(SQLEnum(WACodeLevel))

    wa_code_triggers: Mapped[list["DeliverableWACodeTrigger"]] = relationship(
        back_populates="deliverable", cascade="all, delete-orphan"
    )


class DeliverableWACodeTrigger(Base):
    __tablename__ = "deliverable_wa_code_triggers"

    deliverable_id: Mapped[int] = mapped_column(
        ForeignKey("deliverables.id", ondelete="CASCADE"), primary_key=True
    )
    wa_code_id: Mapped[int] = mapped_column(
        ForeignKey("wa_codes.id", ondelete="CASCADE"), primary_key=True
    )

    deliverable: Mapped["Deliverable"] = relationship(back_populates="wa_code_triggers")
    wa_code: Mapped["WACode"] = relationship()


class ProjectDeliverable(Base, AuditMixin):
    __tablename__ = "project_deliverables"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    deliverable_id: Mapped[int] = mapped_column(
        ForeignKey("deliverables.id", ondelete="RESTRICT"), primary_key=True
    )
    internal_status: Mapped[InternalDeliverableStatus] = mapped_column(
        SQLEnum(InternalDeliverableStatus),
        default=InternalDeliverableStatus.INCOMPLETE,
    )
    sca_status: Mapped[SCADeliverableStatus] = mapped_column(
        SQLEnum(SCADeliverableStatus),
        default=SCADeliverableStatus.PENDING_WA,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="deliverables")
    deliverable: Mapped["Deliverable"] = relationship()


class ProjectBuildingDeliverable(Base, AuditMixin):
    __tablename__ = "project_building_deliverables"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    deliverable_id: Mapped[int] = mapped_column(
        ForeignKey("deliverables.id", ondelete="RESTRICT"), primary_key=True
    )
    school_id: Mapped[int] = mapped_column(primary_key=True)
    internal_status: Mapped[InternalDeliverableStatus] = mapped_column(
        SQLEnum(InternalDeliverableStatus),
        default=InternalDeliverableStatus.INCOMPLETE,
    )
    sca_status: Mapped[SCADeliverableStatus] = mapped_column(
        SQLEnum(SCADeliverableStatus),
        default=SCADeliverableStatus.PENDING_WA,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "school_id"],
            ["project_school_links.project_id", "project_school_links.school_id"],
            ondelete="CASCADE",
        ),
    )

    project: Mapped["Project"] = relationship(back_populates="building_deliverables")
    deliverable: Mapped["Deliverable"] = relationship()
