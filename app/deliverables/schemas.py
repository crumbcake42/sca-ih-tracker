from pydantic import BaseModel, ConfigDict
from app.common.schemas import OptionalField


class DeliverableBase(BaseModel):
    name: str
    description: OptionalField[str] = None


class DeliverableCreate(DeliverableBase):
    pass


class Deliverable(DeliverableBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
