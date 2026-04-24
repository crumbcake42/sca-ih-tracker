from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import TitleEnum
from app.database import AuditMixin, Base


class EmployeeRoleType(Base, AuditMixin):
    __tablename__ = "employee_role_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    roles: Mapped[list["EmployeeRole"]] = relationship(back_populates="role_type")


class Employee(Base, AuditMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    title: Mapped[TitleEnum | None] = mapped_column(SQLEnum(TitleEnum))
    display_name: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(14))
    adp_id: Mapped[str | None] = mapped_column(String(9), unique=True)

    roles: Mapped[list["EmployeeRole"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class EmployeeRole(Base, AuditMixin):
    __tablename__ = "employee_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    role_type_id: Mapped[int] = mapped_column(ForeignKey("employee_role_types.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    employee: Mapped["Employee"] = relationship(back_populates="roles")
    role_type: Mapped["EmployeeRoleType"] = relationship(
        back_populates="roles", lazy="selectin"
    )
