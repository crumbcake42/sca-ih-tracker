from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.employees.models import Employee, EmployeeRole


class TimeEntry(Base, AuditMixin):
    __tablename__ = "time_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "school_id"],
            ["project_school_links.project_id", "project_school_links.school_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    start_datetime: Mapped[datetime] = mapped_column(DateTime)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    employee_role_id: Mapped[int] = mapped_column(
        ForeignKey("employee_roles.id", ondelete="RESTRICT"), index=True
    )
    # Direct FK for referential integrity to projects; also participates in
    # the composite FK to project_school_links above.
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    school_id: Mapped[int] = mapped_column(index=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    employee: Mapped["Employee"] = relationship()
    employee_role: Mapped["EmployeeRole"] = relationship()
