from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.common.enums import TitleEnum


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    title: Mapped[TitleEnum | None] = mapped_column(SQLEnum(TitleEnum))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(14))
    adp_id: Mapped[str | None] = mapped_column(String(9), unique=True)
