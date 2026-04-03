from typing import TYPE_CHECKING
from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, AuditMixin
from app.common.enums import Boro

if TYPE_CHECKING:
    from app.projects.schemas import Project


class School(Base, AuditMixin):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[Boro] = mapped_column(SQLEnum(Boro))
    state: Mapped[str] = mapped_column(String(2), default="NY")
    zip_code: Mapped[str] = mapped_column(String(10))

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="school")
