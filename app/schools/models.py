from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import Boro
from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.projects.models.base import Project


class School(Base, AuditMixin):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[Boro] = mapped_column(SQLEnum(Boro))
    state: Mapped[str] = mapped_column(String(2), default="NY")
    zip_code: Mapped[str] = mapped_column(String(10))

    # Many-to-many back-reference to projects
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        secondary="project_school_links",
        back_populates="schools",
    )
