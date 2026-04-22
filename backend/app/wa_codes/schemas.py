from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import WACodeLevel


class WACodeBase(BaseModel):
    code: str
    description: str
    level: WACodeLevel
    default_fee: Decimal | None = Field(None, ge=0, decimal_places=2)


class WACodeCreate(WACodeBase):
    pass


class WACodeUpdate(BaseModel):
    code: str | None = None
    description: str | None = None
    level: WACodeLevel | None = None
    default_fee: Decimal | None = Field(None, ge=0, decimal_places=2)


class WACode(WACodeBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
