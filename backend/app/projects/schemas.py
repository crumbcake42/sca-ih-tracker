from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROJECT_NUMBER_REGEX = r"^\d{2}\-[1-3]{3}-\d{2}([:;]\d{2})?$"


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
