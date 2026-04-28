from datetime import date as DateField
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.common.enums import DocumentType, EmployeeRoleType


class ProjectDocumentRequirementCreate(BaseModel):
    """Used for manual POST creates (re-occupancy letters, minor letters, etc.)."""

    project_id: int
    document_type: DocumentType
    employee_id: int | None = None
    date: DateField | None = None
    school_id: int | None = None
    expected_role_type: EmployeeRoleType | None = None
    notes: str | None = None
    is_placeholder: bool = False


class ProjectDocumentRequirementUpdate(BaseModel):
    """All fields optional; primary use is toggling is_saved and attaching metadata."""

    is_saved: bool | None = None
    file_id: int | None = None
    employee_id: int | None = None
    date: DateField | None = None
    school_id: int | None = None
    notes: str | None = None


class ProjectDocumentRequirementDismiss(BaseModel):
    dismissal_reason: str

    @field_validator("dismissal_reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("dismissal_reason must not be empty")
        return v


class ProjectDocumentRequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    document_type: DocumentType
    is_saved: bool
    is_placeholder: bool
    employee_id: int | None
    date: DateField | None
    school_id: int | None
    file_id: int | None
    expected_role_type: EmployeeRoleType | None
    wa_code_trigger_id: int | None
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
