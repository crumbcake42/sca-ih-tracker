from pydantic import BaseModel, ConfigDict, EmailStr
from app.common.schemas import OptionalField
from app.common.formatters import format_phone_number
from typing import Annotated
from pydantic import BeforeValidator

PHONE_REGEX = r"^\(\d{3}\) \d{3}-\d{4}$"

OptionalEmail = OptionalField[EmailStr]
OptionalPhone = Annotated[OptionalField[str], BeforeValidator(format_phone_number)]


class HygienistBase(BaseModel):
    first_name: str
    last_name: str
    email: OptionalEmail = None
    phone: OptionalPhone = None


class HygienistCreate(HygienistBase):
    pass


class HygienistUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: OptionalEmail = None
    phone: OptionalPhone = None


class Hygienist(HygienistBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
