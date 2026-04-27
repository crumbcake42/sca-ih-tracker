from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UnfulfilledRequirement(BaseModel):
    """Uniform schema returned by the closure-gate aggregator for any requirement type."""

    requirement_type: str
    project_id: int
    # Opaque stable identifier scoped to (requirement_type, project_id).
    # Deliverable: str(deliverable_id); building deliverable: f"{deliverable_id}:{school_id}".
    # Per-type endpoints introduced in later sessions parse this value.
    requirement_key: str
    label: str
    is_dismissed: bool
    is_dismissable: bool


class WACodeRequirementTriggerCreate(BaseModel):
    wa_code_id: int
    requirement_type_name: str
    template_params: dict = Field(default_factory=dict)


class WACodeRequirementTriggerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wa_code_id: int
    requirement_type_name: str
    template_params: dict
    created_at: datetime
    updated_at: datetime
    created_by_id: int | None
    updated_by_id: int | None
