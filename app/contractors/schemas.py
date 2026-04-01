from pydantic import BaseModel, ConfigDict, Field


class ContractorBase(BaseModel):
    name: str
    address: str
    city: str
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str


class ContractorCreate(ContractorBase):
    pass


class Contractor(ContractorBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
