from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.projects.models import Project


class WorkAuth(Base, AuditMixin):
    __tablename__ = "work_auths"

    id: Mapped[int] = mapped_column(primary_key=True)
    wa_num: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    service_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    project_num: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    initiation_date: Mapped[date] = mapped_column(Date)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), unique=True
    )
    project: Mapped["Project"] = relationship(back_populates="work_auths")
