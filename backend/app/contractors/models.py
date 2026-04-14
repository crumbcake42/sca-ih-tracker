from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.projects.models.links import ProjectContractorLink


class Contractor(Base, AuditMixin):
    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    zip_code: Mapped[str] = mapped_column(String(10))

    # The reverse link to projects
    project_links: Mapped[list["ProjectContractorLink"]] = relationship(
        back_populates="contractor"
    )

    @property
    def active_projects(self):
        """Returns only the projects where this contractor is currently active."""
        return [link.project for link in self.project_links if link.is_current]
