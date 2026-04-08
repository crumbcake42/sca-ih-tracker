from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.common.enums import WACodeLevel


class WACode(Base):
    __tablename__ = "wa_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), unique=True)
    level: Mapped[WACodeLevel] = mapped_column(SQLEnum(WACodeLevel))
