from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.common.enums import Boro


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[Boro] = mapped_column(SQLEnum(Boro))
    state: Mapped[str] = mapped_column(String(2), default="NY")
    zip_code: Mapped[str] = mapped_column(String(10))
