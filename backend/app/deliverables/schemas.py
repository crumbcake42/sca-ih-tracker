from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enums import (
    InternalDeliverableStatus,
    SCADeliverableStatus,
    WACodeLevel,
)
from app.common.schemas import OptionalField


class DeliverableBase(BaseModel):
    name: str
    description: OptionalField[str] = None
    level: WACodeLevel


class DeliverableCreate(DeliverableBase):
    pass


class Deliverable(DeliverableBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ---------------------------------------------------------------------------
# Deliverable WA Code Triggers
# ---------------------------------------------------------------------------


class DeliverableWACodeTriggerCreate(BaseModel):
    wa_code_id: int


class DeliverableWACodeTrigger(BaseModel):
    deliverable_id: int
    wa_code_id: int
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Project Deliverables (project-level)
# ---------------------------------------------------------------------------


class ProjectDeliverableCreate(BaseModel):
    deliverable_id: int
    internal_status: InternalDeliverableStatus = InternalDeliverableStatus.INCOMPLETE
    sca_status: SCADeliverableStatus = SCADeliverableStatus.PENDING_WA
    notes: str | None = None


class ProjectDeliverableUpdate(BaseModel):
    internal_status: InternalDeliverableStatus | None = None
    sca_status: SCADeliverableStatus | None = None
    notes: str | None = None


class ProjectDeliverable(BaseModel):
    project_id: int
    deliverable_id: int
    internal_status: InternalDeliverableStatus
    sca_status: SCADeliverableStatus
    notes: str | None
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Project Building Deliverables (building-level, one per school)
# ---------------------------------------------------------------------------


class ProjectBuildingDeliverableCreate(BaseModel):
    deliverable_id: int
    school_id: int
    internal_status: InternalDeliverableStatus = InternalDeliverableStatus.INCOMPLETE
    sca_status: SCADeliverableStatus = SCADeliverableStatus.PENDING_WA
    notes: str | None = None


class ProjectBuildingDeliverableUpdate(BaseModel):
    internal_status: InternalDeliverableStatus | None = None
    sca_status: SCADeliverableStatus | None = None
    notes: str | None = None


class ProjectBuildingDeliverable(BaseModel):
    project_id: int
    deliverable_id: int
    school_id: int
    internal_status: InternalDeliverableStatus
    sca_status: SCADeliverableStatus
    notes: str | None
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)
