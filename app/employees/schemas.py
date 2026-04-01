from pydantic import BaseModel, ConfigDict, EmailStr, Field, BeforeValidator
from typing import Annotated

from app.common.enums import TitleEnum
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
    title: OptionalTitle = None
    email: OptionalEmail = None
    phone: OptionalPhone = Field(None, pattern=PHONE_REGEX, max_length=14)
    adp_id: OptionalString = Field(None, max_length=9, pattern=r"^[a-zA-Z0-9]{9}$")


class EmployeeCreate(EmployeeBase):
    pass


class Employee(EmployeeBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
