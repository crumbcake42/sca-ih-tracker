from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.common.enums import CPRStageStatus


class ContractorPaymentRecordCreate(BaseModel):
    """Used for manual POST creates when the system event was missed or for admin correction."""

    project_id: int
    contractor_id: int
    notes: str | None = None


class ContractorPaymentRecordUpdate(BaseModel):
    """All fields optional; primary use is advancing RFA/RFP stage dates and statuses."""

    is_required: bool | None = None
    rfa_submitted_at: datetime | None = None
    rfa_internal_status: CPRStageStatus | None = None
    rfa_internal_resolved_at: datetime | None = None
    rfa_sca_status: CPRStageStatus | None = None
    rfa_sca_resolved_at: datetime | None = None
    rfp_submitted_at: datetime | None = None
    rfp_internal_status: CPRStageStatus | None = None
    rfp_internal_resolved_at: datetime | None = None
    rfp_saved_at: datetime | None = None
    file_id: int | None = None
    notes: str | None = None


class ContractorPaymentRecordDismiss(BaseModel):
    dismissal_reason: str

    @field_validator("dismissal_reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("dismissal_reason must not be empty")
        return v


class ContractorPaymentRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    contractor_id: int
    is_required: bool
    # RFA sub-flow
    rfa_submitted_at: datetime | None
    rfa_internal_status: CPRStageStatus | None
    rfa_internal_resolved_at: datetime | None
    rfa_sca_status: CPRStageStatus | None
    rfa_sca_resolved_at: datetime | None
    # RFP sub-flow
    rfp_submitted_at: datetime | None
    rfp_internal_status: CPRStageStatus | None
    rfp_internal_resolved_at: datetime | None
    rfp_saved_at: datetime | None
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
