from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import WACodeLevel
from app.database import Base


class WACode(Base):
    __tablename__ = "wa_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), unique=True)
    level: Mapped[WACodeLevel] = mapped_column(SQLEnum(WACodeLevel))
