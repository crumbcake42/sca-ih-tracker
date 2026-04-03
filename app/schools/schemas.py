from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.common.enums import Boro


class SchoolBase(BaseModel):
    code: str = Field(..., min_length=4, max_length=4)
    name: str
    address: str
    city: Boro
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str


class SchoolCreate(SchoolBase):
    pass


class School(SchoolBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
