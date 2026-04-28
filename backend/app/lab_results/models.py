from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import EmployeeRoleType, SampleBatchStatus
from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.employees.models import Employee
    from app.time_entries.models import TimeEntry
    from app.wa_codes.models import WACode


# ---------------------------------------------------------------------------
# Config layer — admin-managed, seeded on first deploy, rarely change
# ---------------------------------------------------------------------------


class SampleType(Base, AuditMixin):
    __tablename__ = "sample_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allows_multiple_inspectors: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
    )

    subtypes: Mapped[list["SampleSubtype"]] = relationship(
        back_populates="sample_type", cascade="all, delete-orphan", lazy="selectin"
    )
    unit_types: Mapped[list["SampleUnitType"]] = relationship(
        back_populates="sample_type", cascade="all, delete-orphan", lazy="selectin"
    )
    turnaround_options: Mapped[list["TurnaroundOption"]] = relationship(
        back_populates="sample_type", cascade="all, delete-orphan", lazy="selectin"
    )
    required_roles: Mapped[list["SampleTypeRequiredRole"]] = relationship(
        back_populates="sample_type", cascade="all, delete-orphan", lazy="selectin"
    )
    wa_codes: Mapped[list["SampleTypeWACode"]] = relationship(
        back_populates="sample_type", cascade="all, delete-orphan", lazy="selectin"
    )


class SampleSubtype(Base, AuditMixin):
    __tablename__ = "sample_subtypes"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_type_id: Mapped[int] = mapped_column(
        ForeignKey("sample_types.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))

    sample_type: Mapped["SampleType"] = relationship(back_populates="subtypes")


class SampleUnitType(Base, AuditMixin):
    __tablename__ = "sample_unit_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_type_id: Mapped[int] = mapped_column(
        ForeignKey("sample_types.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))

    sample_type: Mapped["SampleType"] = relationship(back_populates="unit_types")


class TurnaroundOption(Base, AuditMixin):
    __tablename__ = "turnaround_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_type_id: Mapped[int] = mapped_column(
        ForeignKey("sample_types.id", ondelete="CASCADE"), index=True
    )
    hours: Mapped[int] = mapped_column()
    label: Mapped[str] = mapped_column(String(50))

    sample_type: Mapped["SampleType"] = relationship(back_populates="turnaround_options")


class SampleTypeRequiredRole(Base, AuditMixin):
    """Roles an employee must hold to collect this sample type.
    Uses a surrogate PK so role_type values (which contain spaces/slashes)
    don't appear in URL paths."""

    __tablename__ = "sample_type_required_roles"
    __table_args__ = (
        UniqueConstraint("sample_type_id", "role_type",
                         name="uq_sample_type_required_roles"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_type_id: Mapped[int] = mapped_column(
        ForeignKey("sample_types.id", ondelete="CASCADE"), index=True
    )
    role_type: Mapped[EmployeeRoleType] = mapped_column(SQLEnum(EmployeeRoleType))

    sample_type: Mapped["SampleType"] = relationship(back_populates="required_roles")


class SampleTypeWACode(Base, AuditMixin):
    """WA codes that must be on the work auth to bill this sample type."""

    __tablename__ = "sample_type_wa_codes"

    sample_type_id: Mapped[int] = mapped_column(
        ForeignKey("sample_types.id", ondelete="CASCADE"), primary_key=True
    )
    wa_code_id: Mapped[int] = mapped_column(
        ForeignKey("wa_codes.id", ondelete="RESTRICT"), primary_key=True
    )

    sample_type: Mapped["SampleType"] = relationship(back_populates="wa_codes")
    wa_code: Mapped["WACode"] = relationship()


# ---------------------------------------------------------------------------
# Data layer — recorded per job
# ---------------------------------------------------------------------------


class SampleBatch(Base, AuditMixin):
    __tablename__ = "sample_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_type_id: Mapped[int] = mapped_column(
        ForeignKey("sample_types.id", ondelete="RESTRICT"), index=True
    )
    sample_subtype_id: Mapped[int | None] = mapped_column(
        ForeignKey("sample_subtypes.id", ondelete="SET NULL"), nullable=True
    )
    turnaround_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("turnaround_options.id", ondelete="SET NULL"), nullable=True
    )
    time_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("time_entries.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    batch_num: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[SampleBatchStatus] = mapped_column(
        SQLEnum(SampleBatchStatus),
        nullable=False,
        default=SampleBatchStatus.ACTIVE,
        server_default=SampleBatchStatus.ACTIVE,
    )
    date_collected: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sample_type: Mapped["SampleType"] = relationship()
    subtype: Mapped["SampleSubtype | None"] = relationship()
    turnaround_option: Mapped["TurnaroundOption | None"] = relationship()
    time_entry: Mapped["TimeEntry | None"] = relationship()
    units: Mapped[list["SampleBatchUnit"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan", lazy="selectin"
    )
    inspectors: Mapped[list["SampleBatchInspector"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan", lazy="selectin"
    )


class SampleBatchUnit(Base):
    """One row per unit type in a batch. quantity is the count of individual samples."""

    __tablename__ = "sample_batch_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("sample_batches.id", ondelete="CASCADE"), index=True
    )
    sample_unit_type_id: Mapped[int] = mapped_column(
        ForeignKey("sample_unit_types.id", ondelete="RESTRICT")
    )
    quantity: Mapped[int] = mapped_column()
    # Denormalized from sample_rates at record time; null until billing is implemented.
    unit_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    batch: Mapped["SampleBatch"] = relationship(back_populates="units")
    unit_type: Mapped["SampleUnitType"] = relationship()


class SampleBatchInspector(Base):
    __tablename__ = "sample_batch_inspectors"

    batch_id: Mapped[int] = mapped_column(
        ForeignKey("sample_batches.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), primary_key=True
    )

    batch: Mapped["SampleBatch"] = relationship(back_populates="inspectors")
    employee: Mapped["Employee"] = relationship()
