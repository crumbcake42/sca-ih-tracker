from pydantic import BaseModel, ConfigDict
from app.common.enums import WACodeLevel


class WACodeBase(BaseModel):
    code: str
    description: str
    level: WACodeLevel


class WACodeCreate(WACodeBase):
    pass


class WACode(WACodeBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
