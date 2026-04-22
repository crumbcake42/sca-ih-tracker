from pydantic import BaseModel, ConfigDict, Field


class ContractorBase(BaseModel):
    name: str
    address: str
    city: str
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str


class ContractorCreate(ContractorBase):
    pass


class ContractorUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = Field(None, min_length=2, max_length=2)
    zip_code: str | None = None


class Contractor(ContractorBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
