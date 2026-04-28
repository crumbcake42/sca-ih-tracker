from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class LabReportRequirementUpdate(BaseModel):
    is_saved: bool | None = None
    file_id: int | None = None


class LabReportRequirementDismiss(BaseModel):
    dismissal_reason: str

    @field_validator("dismissal_reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("dismissal_reason must not be empty")
        return v


class LabReportRequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    sample_batch_id: int
    is_saved: bool
    saved_at: datetime | None
    file_id: int | None
    # DismissibleMixin
    dismissal_reason: str | None
    dismissed_by_id: int | None
    dismissed_at: datetime | None
    # AuditMixin
    created_at: datetime
    updated_at: datetime
    created_by_id: int | None
    updated_by_id: int | None
    # Protocol fields — sourced from model properties via from_attributes=True
    label: str
    is_fulfilled: bool
    is_dismissed: bool
