from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# This block is ONLY seen by your IDE/Type Checker
if TYPE_CHECKING:
    from .base import Project
    from app.contractors.models import Contractor


class ProjectContractor(Base):
    __tablename__ = "project_contractors"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    contractor_id: Mapped[int] = mapped_column(
        ForeignKey("contractors.id"), primary_key=True
    )

    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # String reference "Project" matches the class name in base.py
    project: Mapped["Project"] = relationship(back_populates="contractor_links")
    contractor: Mapped["Contractor"] = relationship()
