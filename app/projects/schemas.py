from pydantic import BaseModel, ConfigDict


class ProjectBase(BaseModel):
    title: str
    school_id: int


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
