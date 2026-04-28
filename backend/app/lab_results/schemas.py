from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import EmployeeRoleType, SampleBatchStatus

# ---------------------------------------------------------------------------
# Config schemas
# ---------------------------------------------------------------------------


class SampleSubtypeCreate(BaseModel):
    name: str = Field(..., max_length=100)


class SampleSubtypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sample_type_id: int
    name: str


class SampleUnitTypeCreate(BaseModel):
    name: str = Field(..., max_length=100)


class SampleUnitTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sample_type_id: int
    name: str


class TurnaroundOptionCreate(BaseModel):
    hours: int = Field(..., gt=0)
    label: str = Field(..., max_length=50)


class TurnaroundOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sample_type_id: int
    hours: int
    label: str


class SampleTypeRequiredRoleCreate(BaseModel):
    role_type: EmployeeRoleType


class SampleTypeRequiredRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sample_type_id: int
    role_type: EmployeeRoleType


class SampleTypeWACodeCreate(BaseModel):
    wa_code_id: int


class SampleTypeWACodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sample_type_id: int
    wa_code_id: int


class SampleTypeCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    allows_multiple_inspectors: bool = True


class SampleTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    allows_multiple_inspectors: bool | None = None


class SampleTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    allows_multiple_inspectors: bool
    subtypes: list[SampleSubtypeRead]
    unit_types: list[SampleUnitTypeRead]
    turnaround_options: list[TurnaroundOptionRead]
    required_roles: list[SampleTypeRequiredRoleRead]
    wa_codes: list[SampleTypeWACodeRead]


# ---------------------------------------------------------------------------
# Data schemas
# ---------------------------------------------------------------------------


class SampleBatchUnitCreate(BaseModel):
    sample_unit_type_id: int
    quantity: int = Field(..., ge=1)


class SampleBatchUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: int
    sample_unit_type_id: int
    quantity: int
    unit_rate: Decimal | None


class SampleBatchInspectorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    batch_id: int
    employee_id: int


class SampleBatchCreate(BaseModel):
    sample_type_id: int
    sample_subtype_id: int | None = None
    turnaround_option_id: int | None = None
    time_entry_id: int | None = None
    batch_num: str = Field(..., max_length=50)
    date_collected: date
    notes: str | None = None
    units: list[SampleBatchUnitCreate] = Field(..., min_length=1)
    inspector_ids: list[int] = Field(..., min_length=1)


class SampleBatchUpdate(BaseModel):
    date_collected: date | None = None
    notes: str | None = None


class SampleBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sample_type_id: int
    sample_subtype_id: int | None
    turnaround_option_id: int | None
    time_entry_id: int | None
    batch_num: str
    status: SampleBatchStatus
    date_collected: date
    notes: str | None
    created_at: datetime
    units: list[SampleBatchUnitRead]
    inspectors: list[SampleBatchInspectorRead]


class QuickAddBatchCreate(BaseModel):
    """Creates a TimeEntry (assumed) and a SampleBatch atomically."""
    # Time entry fields
    employee_id: int
    employee_role_id: int
    project_id: int
    school_id: int
    date_on_site: date
    # Batch fields (same as SampleBatchCreate minus time_entry_id)
    sample_type_id: int
    sample_subtype_id: int | None = None
    turnaround_option_id: int | None = None
    batch_num: str = Field(..., max_length=50)
    date_collected: date
    notes: str | None = None
    units: list[SampleBatchUnitCreate] = Field(..., min_length=1)
    inspector_ids: list[int] = Field(..., min_length=1)
