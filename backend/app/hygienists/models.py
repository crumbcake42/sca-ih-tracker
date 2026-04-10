from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.projects.models.links import ProjectHygienistLink


class Hygienist(Base):
    __tablename__ = "hygienists"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)

    project_links: Mapped[list["ProjectHygienistLink"]] = relationship(
        back_populates="hygienist"
    )
