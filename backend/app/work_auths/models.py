from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import RFAAction, RFAStatus, WACodeStatus
from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.projects.models import Project
    from app.users.models import User
    from app.wa_codes.models import WACode


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

    project_codes: Mapped[list["WorkAuthProjectCode"]] = relationship(
        back_populates="work_auth", cascade="all, delete-orphan"
    )
    building_codes: Mapped[list["WorkAuthBuildingCode"]] = relationship(
        back_populates="work_auth", cascade="all, delete-orphan"
    )
    rfas: Mapped[list["RFA"]] = relationship(
        back_populates="work_auth", cascade="all, delete-orphan"
    )


class WorkAuthProjectCode(Base, AuditMixin):
    __tablename__ = "work_auth_project_codes"

    work_auth_id: Mapped[int] = mapped_column(
        ForeignKey("work_auths.id", ondelete="CASCADE"), primary_key=True
    )
    wa_code_id: Mapped[int] = mapped_column(
        ForeignKey("wa_codes.id", ondelete="RESTRICT"), primary_key=True
    )
    fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[WACodeStatus] = mapped_column(
        SQLEnum(WACodeStatus), default=WACodeStatus.RFA_NEEDED
    )
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    work_auth: Mapped["WorkAuth"] = relationship(back_populates="project_codes")
    wa_code: Mapped["WACode"] = relationship()


class WorkAuthBuildingCode(Base, AuditMixin):
    __tablename__ = "work_auth_building_codes"

    work_auth_id: Mapped[int] = mapped_column(
        ForeignKey("work_auths.id", ondelete="CASCADE"), primary_key=True
    )
    wa_code_id: Mapped[int] = mapped_column(
        ForeignKey("wa_codes.id", ondelete="RESTRICT"), primary_key=True
    )
    project_id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(primary_key=True)
    budget: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[WACodeStatus] = mapped_column(
        SQLEnum(WACodeStatus), default=WACodeStatus.RFA_NEEDED
    )
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "school_id"],
            ["project_school_links.project_id", "project_school_links.school_id"],
            ondelete="RESTRICT",
        ),
    )

    work_auth: Mapped["WorkAuth"] = relationship(back_populates="building_codes")
    wa_code: Mapped["WACode"] = relationship()


class RFA(Base, AuditMixin):
    __tablename__ = "rfas"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_auth_id: Mapped[int] = mapped_column(
        ForeignKey("work_auths.id", ondelete="CASCADE")
    )
    status: Mapped[RFAStatus] = mapped_column(
        SQLEnum(RFAStatus), default=RFAStatus.PENDING
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(nullable=True)

    work_auth: Mapped["WorkAuth"] = relationship(back_populates="rfas")
    submitted_by: Mapped["User | None"] = relationship(foreign_keys="[RFA.submitted_by_id]")
    project_codes: Mapped[list["RFAProjectCode"]] = relationship(
        back_populates="rfa", cascade="all, delete-orphan", lazy="selectin"
    )
    building_codes: Mapped[list["RFABuildingCode"]] = relationship(
        back_populates="rfa", cascade="all, delete-orphan", lazy="selectin"
    )


class RFAProjectCode(Base, AuditMixin):
    __tablename__ = "rfa_project_codes"

    rfa_id: Mapped[int] = mapped_column(
        ForeignKey("rfas.id", ondelete="CASCADE"), primary_key=True
    )
    wa_code_id: Mapped[int] = mapped_column(
        ForeignKey("wa_codes.id", ondelete="RESTRICT"), primary_key=True
    )
    action: Mapped[RFAAction] = mapped_column(SQLEnum(RFAAction))

    rfa: Mapped["RFA"] = relationship(back_populates="project_codes")
    wa_code: Mapped["WACode"] = relationship()


class RFABuildingCode(Base, AuditMixin):
    __tablename__ = "rfa_building_codes"

    rfa_id: Mapped[int] = mapped_column(
        ForeignKey("rfas.id", ondelete="CASCADE"), primary_key=True
    )
    wa_code_id: Mapped[int] = mapped_column(
        ForeignKey("wa_codes.id", ondelete="RESTRICT"), primary_key=True
    )
    project_id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[RFAAction] = mapped_column(SQLEnum(RFAAction))
    budget_adjustment: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "school_id"],
            ["project_school_links.project_id", "project_school_links.school_id"],
            ondelete="RESTRICT",
        ),
    )

    rfa: Mapped["RFA"] = relationship(back_populates="building_codes")
    wa_code: Mapped["WACode"] = relationship()
