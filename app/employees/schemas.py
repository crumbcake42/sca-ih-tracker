from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.common.enums import TitleEnum


class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    title: TitleEnum | None = None
    email: EmailStr | None = None
    phone: str | None = None
    adp_id: str | None = Field(None, pattern=r"^[a-zA-Z0-9]{9}$")


class EmployeeCreate(EmployeeBase):
    pass


class Employee(EmployeeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
