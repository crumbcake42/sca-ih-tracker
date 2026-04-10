from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import AuditMixin, Base

from .links import project_school_links

# These imports only happen for the Type Checker/IDE
if TYPE_CHECKING:
    from app.schools.models import School
    from app.work_auths.models import WorkAuth

    from .links import ProjectContractorLink, ProjectHygienistLink, ProjectManagerAssignment


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

    # One hygienist per project — uselist=False since project_id is the PK
    # on the link table, making this a one-to-one from the project side.
    hygienist_link: Mapped["ProjectHygienistLink | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )

    # Append-only manager assignment history. Use the active_manager
    # property for the current assignment.
    manager_assignments: Mapped[list["ProjectManagerAssignment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    @property
    def active_manager(self) -> "ProjectManagerAssignment | None":
        return next(
            (a for a in self.manager_assignments if a.unassigned_at is None), None
        )

    work_auths: Mapped[list["WorkAuth"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
