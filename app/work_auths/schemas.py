from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import WACodeStatus


class WorkAuthBase(BaseModel):
    wa_num: str = Field(..., max_length=50)
    service_id: str = Field(..., max_length=50)
    project_num: str = Field(..., max_length=50)
    initiation_date: date
    project_id: int


class WorkAuthCreate(WorkAuthBase):
    pass


class WorkAuthUpdate(BaseModel):
    wa_num: str | None = Field(None, max_length=50)
    service_id: str | None = Field(None, max_length=50)
    project_num: str | None = Field(None, max_length=50)
    initiation_date: date | None = None
    is_saved: bool | None = None


class WorkAuth(WorkAuthBase):
    id: int
    is_saved: bool
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Work Auth Project Codes
# ---------------------------------------------------------------------------


class WorkAuthProjectCodeCreate(BaseModel):
    wa_code_id: int
    fee: Decimal = Field(..., ge=0, decimal_places=2)
    status: WACodeStatus = WACodeStatus.RFA_NEEDED


class WorkAuthProjectCodeUpdate(BaseModel):
    fee: Decimal | None = Field(None, ge=0, decimal_places=2)
    status: WACodeStatus | None = None


class WorkAuthProjectCode(BaseModel):
    work_auth_id: int
    wa_code_id: int
    fee: Decimal
    status: WACodeStatus
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Work Auth Building Codes
# ---------------------------------------------------------------------------


class WorkAuthBuildingCodeCreate(BaseModel):
    wa_code_id: int
    school_id: int
    budget: Decimal = Field(..., ge=0, decimal_places=2)
    status: WACodeStatus = WACodeStatus.RFA_NEEDED


class WorkAuthBuildingCodeUpdate(BaseModel):
    budget: Decimal | None = Field(None, ge=0, decimal_places=2)
    status: WACodeStatus | None = None


class WorkAuthBuildingCode(BaseModel):
    work_auth_id: int
    wa_code_id: int
    project_id: int
    school_id: int
    budget: Decimal
    status: WACodeStatus
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)
