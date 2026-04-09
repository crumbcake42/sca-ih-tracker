from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# This block is ONLY seen by your IDE/Type Checker
if TYPE_CHECKING:
    from app.contractors.models import Contractor
    from app.hygienists.models import Hygienist
    from app.users.models import User

    from .base import Project


# Simple association table — no extra columns needed for school links
project_school_links = Table(
    "project_school_links",
    Base.metadata,
    Column(
        "project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("school_id", ForeignKey("schools.id", ondelete="CASCADE"), primary_key=True),
)


class ProjectContractorLink(Base):
    __tablename__ = "project_contractors_links"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    contractor_id: Mapped[int] = mapped_column(
        ForeignKey("contractors.id"), primary_key=True
    )

    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # String reference "Project" matches the class name in base.py
    project: Mapped["Project"] = relationship(back_populates="contractor_links")
    contractor: Mapped["Contractor"] = relationship()


class ProjectHygienistLink(Base):
    """
    Tracks which hygienist is assigned to a project.
    One hygienist per project at a time — enforced by the unique constraint
    on project_id. Modelled as a link table rather than a direct FK on
    projects so assignment history can be added later without a schema change.
    """

    __tablename__ = "project_hygienist_links"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    hygienist_id: Mapped[int] = mapped_column(
        ForeignKey("hygienists.id", ondelete="RESTRICT")
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="hygienist_link")
    hygienist: Mapped["Hygienist"] = relationship(back_populates="project_links")


class ProjectManagerAssignment(Base):
    """
    Append-only audit trail of manager assignments per project.

    Rules (enforced at the service layer):
    - At most one active assignment per project (unassigned_at IS NULL).
    - Reassigning closes the current row (sets unassigned_at) then inserts
      a new one — never update in-place.
    - Rows are never deleted; the full history is always preserved.
    """

    __tablename__ = "project_manager_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    assigned_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="manager_assignments")
    manager: Mapped["User"] = relationship(
        foreign_keys="ProjectManagerAssignment.user_id"
    )
    assigned_by: Mapped["User | None"] = relationship(
        foreign_keys="ProjectManagerAssignment.assigned_by_id"
    )
