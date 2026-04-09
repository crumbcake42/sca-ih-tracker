from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import AuditMixin, Base

from .links import project_school_links

# These imports only happen for the Type Checker/IDE
if TYPE_CHECKING:
    from app.schools.models import School

    from .links import ProjectContractorLink


class Project(Base, AuditMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    project_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # Many-to-many: a project takes place at one or more schools
    schools: Mapped[list["School"]] = relationship(
        secondary=project_school_links,
        back_populates="projects",
    )

    @property
    def school_ids(self) -> list[int]:
        return [s.id for s in self.schools]

    # Single contractor (currently active)
    contractor: Mapped["ProjectContractorLink | None"] = relationship(
        primaryjoin="and_(Project.id == ProjectContractorLink.project_id, ProjectContractorLink.is_current)",
        viewonly=True,
        uselist=False,
    )

    # All contractors
    contractor_links: Mapped[list["ProjectContractorLink"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
