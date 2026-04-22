from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, model_validator

from app.common.enums import EmployeeRoleType, TitleEnum
from app.common.formatters import format_phone_number
from app.common.schemas import OptionalField

PHONE_REGEX = r"^\(\d{3}\) \d{3}-\d{4}$"

OptionalString = OptionalField[str]
OptionalTitle = OptionalField[TitleEnum]
OptionalEmail = OptionalField[EmailStr]
# Chain:
#   1. Handle empty strings
#   2. Format digits to (XXX) XXX-XXXX
OptionalPhone = Annotated[OptionalField[str], BeforeValidator(format_phone_number)]


class EmployeeBase(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    display_name: OptionalString = Field(None, max_length=255)
    title: OptionalTitle = None
    email: OptionalEmail = None
    phone: OptionalPhone = Field(None, pattern=PHONE_REGEX, max_length=14)
    adp_id: OptionalString = Field(None, max_length=9, pattern=r"^[a-zA-Z0-9]{9}$")


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    display_name: OptionalString = Field(None, max_length=255)
    title: OptionalTitle = None
    email: OptionalEmail = None
    phone: OptionalPhone = Field(None, pattern=PHONE_REGEX, max_length=14)
    adp_id: OptionalString = Field(None, max_length=9, pattern=r"^[a-zA-Z0-9]{9}$")


class Employee(EmployeeBase):
    id: int
    created_by_id: int | None = None
    updated_by_id: int | None = None
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class EmployeeRoleBase(BaseModel):
    role_type: EmployeeRoleType
    start_date: date
    end_date: date | None = None
    hourly_rate: Decimal = Field(..., ge=0, decimal_places=2)

    @model_validator(mode="after")
    def end_after_start(self) -> "EmployeeRoleBase":
        if self.end_date is not None and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class EmployeeRoleCreate(EmployeeRoleBase):
    pass


class EmployeeRoleUpdate(BaseModel):
    end_date: date | None = None
    hourly_rate: Decimal | None = Field(None, ge=0, decimal_places=2)


class EmployeeRole(EmployeeRoleBase):
    id: int
    employee_id: int
    model_config = ConfigDict(from_attributes=True)
