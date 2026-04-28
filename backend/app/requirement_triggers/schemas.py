from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
