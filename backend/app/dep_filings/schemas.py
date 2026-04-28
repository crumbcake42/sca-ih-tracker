from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class DEPFilingFormCreate(BaseModel):
    code: str
    label: str
    is_default_selected: bool = False
    display_order: int = 0


class DEPFilingFormUpdate(BaseModel):
    code: str | None = None
    label: str | None = None
    is_default_selected: bool | None = None
    display_order: int | None = None


class DEPFilingFormRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    is_default_selected: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
    created_by_id: int | None
    updated_by_id: int | None


class ProjectDEPFilingCreate(BaseModel):
    """POST /projects/{id}/dep-filings body: manager selects which forms apply."""

    form_ids: list[int]


class ProjectDEPFilingUpdate(BaseModel):
    is_saved: bool | None = None
    file_id: int | None = None
    notes: str | None = None


class ProjectDEPFilingDismiss(BaseModel):
    dismissal_reason: str

    @field_validator("dismissal_reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("dismissal_reason must not be empty")
        return v


class ProjectDEPFilingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    dep_filing_form_id: int
    is_saved: bool
    saved_at: datetime | None
    file_id: int | None
    notes: str | None
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
