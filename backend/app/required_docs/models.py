from datetime import date as DateType
from typing import ClassVar

from sqlalchemy import Date, ForeignKey, Index, Integer, Text, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import DocumentType, EmployeeRoleType
from app.common.requirements import DismissibleMixin
from app.database import AuditMixin, Base


class ProjectDocumentRequirement(Base, AuditMixin, DismissibleMixin):
    __tablename__ = "project_document_requirements"

    # Protocol class-level identifiers
    requirement_type: ClassVar[str] = "project_document"
    is_dismissable: ClassVar[bool] = True

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType), nullable=False, index=True
    )
    is_saved: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_placeholder: Mapped[bool] = mapped_column(default=False, nullable=False)
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    date: Mapped[DateType | None] = mapped_column(Date, nullable=True, index=True)
    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("schools.id", ondelete="SET NULL"), nullable=True, index=True
    )
    file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_role_type: Mapped[EmployeeRoleType | None] = mapped_column(
        SQLEnum(EmployeeRoleType), nullable=True
    )
    # Tracks which wa_code_requirement_trigger materialized this row; used by WA_CODE_REMOVED
    # to identify rows eligible for pristine cleanup (Decision #6).
    wa_code_trigger_id: Mapped[int | None] = mapped_column(
        ForeignKey("wa_code_requirement_triggers.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # Prevents duplicate live rows for the same (project, doc type, employee, date, school).
        # The WHERE clause ensures dismissed rows don't block re-materialization.
        Index(
            "ix_uq_proj_doc_req_active",
            "project_id",
            "document_type",
            "employee_id",
            "date",
            "school_id",
            unique=True,
            sqlite_where=text("dismissed_at IS NULL"),
        ),
        Index("ix_proj_doc_req_status", "project_id", "is_saved", "dismissed_at"),
    )

    @property
    def label(self) -> str:
        if self.document_type == DocumentType.DAILY_LOG:
            date_str = self.date.isoformat() if self.date else "pending"
            return f"Daily Log ({date_str})"
        if self.document_type == DocumentType.REOCCUPANCY_LETTER:
            return "Re-Occupancy Letter"
        if self.document_type == DocumentType.MINOR_LETTER:
            return "Minor Letter"
        return str(self.document_type)

    @property
    def is_dismissed(self) -> bool:
        return self.dismissed_at is not None

    @property
    def is_fulfilled(self) -> bool:
        return self.is_saved
