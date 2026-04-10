from datetime import date

from pydantic import BaseModel, ConfigDict, Field


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
