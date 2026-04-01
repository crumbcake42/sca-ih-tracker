from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# These imports only happen for the Type Checker/IDE
if TYPE_CHECKING:
    from app.schools.models import School
    from app.contractors.models import Contractor
    from app.employees.models import Employee


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)

    # Foreign Keys
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"))
    contractor_id: Mapped[int | None] = mapped_column(ForeignKey("contractors.id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))

    # Relationships (Type hinted as strings to avoid import loops)
    school: Mapped["School"] = relationship("School")
    contractor: Mapped["Contractor | None"] = relationship("Contractor")
    manager: Mapped["Employee | None"] = relationship("Employee")
