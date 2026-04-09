from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import AuditMixin, Base

# This block is ONLY seen by your IDE/Type Checker
if TYPE_CHECKING:
    from app.contractors.models import Contractor

    from .base import Project


# Simple association table — no extra columns needed for school links
project_school_links = Table(
    "project_school_links",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("school_id", ForeignKey("schools.id", ondelete="CASCADE"), primary_key=True),
)


class ProjectContractorLink(Base, AuditMixin):
    __tablename__ = "project_contractors_links"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    contractor_id: Mapped[int] = mapped_column(
        ForeignKey("contractors.id"), primary_key=True
    )

    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # String reference "Project" matches the class name in base.py
    project: Mapped["Project"] = relationship(back_populates="contractor_links")
    contractor: Mapped["Contractor"] = relationship()
