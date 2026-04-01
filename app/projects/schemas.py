from pydantic import BaseModel, ConfigDict, Field

PROJECT_NUMBER_REGEX = r"^\d{2}\-[1-3]{3}-\d{2}([:;]\d{2})?$"


class ProjectBase(BaseModel):
    title: str
    school_id: int
    project_number: str = Field(
        ...,
        pattern=PROJECT_NUMBER_REGEX,
        description="Standard Agency Project Number Format (YY-Type-ID[:Sub])",
    )


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
