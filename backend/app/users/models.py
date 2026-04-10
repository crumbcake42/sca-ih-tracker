from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.projects.models.links import ProjectManagerAssignment

# Association Table: Links Roles to Permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)  # e.g., "project:create"


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)  # e.g., "admin"

    # Relationships
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions, lazy="joined"
    )


# Update User model to link to Role
class User(Base, AuditMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20))

    # We store the hash, never the plain text password
    hashed_password: Mapped[str] = mapped_column(String(255))

    # server_default=func.now() lets the DB handle the timestamp
    date_created: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    role: Mapped["Role"] = relationship(lazy="joined")

    project_assignments: Mapped[list["ProjectManagerAssignment"]] = relationship(
        back_populates="manager",
        foreign_keys="ProjectManagerAssignment.user_id",
    )
