from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, AuditMixin

# These imports only happen for the Type Checker/IDE
if TYPE_CHECKING:
    from app.schools.models import School
    from app.users.models import User
    from .links import ProjectContractorLink


class Project(Base, AuditMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    # We use String(20) because your regex maxes out around 12-15 characters.
    # index=True is critical for your Batch Import performance.
    project_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # Foreign Keys
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"))
    # contractor_id: Mapped[int | None] = mapped_column(ForeignKey("contractors.id"))
    # manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))

    # Relationships (Type hinted as strings to avoid import loops)
    school: Mapped["School"] = relationship("School")
    # manager: Mapped["User | None"] = relationship("User")

    # Single contractor
    contractor: Mapped["ProjectContractorLink | None"] = relationship(
        primaryjoin="and_(Project.id == ProjectContractorLink.project_id, ProjectContractorLink.is_current == True)",
        viewonly=True,
        uselist=False,
    )

    # All contractors
    contractor_links: Mapped[list["ProjectContractorLink"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
