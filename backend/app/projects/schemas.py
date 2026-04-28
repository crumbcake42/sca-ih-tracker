from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.common.enums import ProjectStatus
from app.notes.schemas import BlockingIssue

PROJECT_NUMBER_REGEX = r"^\d{2}-\d{3}-\d{4}([:;]\d{2,})?$"


class ProjectBase(BaseModel):
    name: str
    project_number: str = Field(
        ...,
        pattern=PROJECT_NUMBER_REGEX,
        description="Standard Agency Project Number Format (YY-Type-ID[:Sub])",
    )


class ProjectCreate(ProjectBase):
    school_ids: list[int] = Field(..., min_length=1)


class HygienistAssignment(BaseModel):
    """Nested read schema — embedded in Project responses."""

    hygienist_id: int
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssignHygienist(BaseModel):
    """Write schema for POST /projects/{id}/hygienist."""

    hygienist_id: int


class ManagerAssignment(BaseModel):
    """Read schema for a single manager assignment record."""

    id: int
    user_id: int
    assigned_by_id: int | None
    assigned_at: datetime
    unassigned_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AssignManager(BaseModel):
    """Write schema for POST /projects/{id}/manager."""

    user_id: int


class ProjectStatusRead(BaseModel):
    project_id: int
    status: ProjectStatus
    has_work_auth: bool
    pending_rfa_count: int
    outstanding_deliverable_count: int
    unconfirmed_time_entry_count: int
    unfulfilled_requirement_count: int
    blocking_issues: list[BlockingIssue]


class Project(ProjectBase):
    id: int
    school_ids: list[int] = Field(default_factory=list)
    hygienist: HygienistAssignment | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def map_hygienist_link(cls, data: Any) -> Any:
        # When building from an ORM object, the relationship is called
        # `hygienist_link`. Map it to `hygienist` for the API response.
        if hasattr(data, "hygienist_link"):
            data.__dict__.setdefault("hygienist", data.hygienist_link)
        return data
