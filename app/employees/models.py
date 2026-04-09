from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import EmployeeRoleType, TitleEnum
from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    title: Mapped[TitleEnum | None] = mapped_column(SQLEnum(TitleEnum))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(14))
    adp_id: Mapped[str | None] = mapped_column(String(9), unique=True)

    roles: Mapped[list["EmployeeRole"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class EmployeeRole(Base):
    __tablename__ = "employee_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    role_type: Mapped[EmployeeRoleType] = mapped_column(SQLEnum(EmployeeRoleType))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    employee: Mapped["Employee"] = relationship(back_populates="roles")
