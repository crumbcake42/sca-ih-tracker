from pydantic import BaseModel, ConfigDict, Field

PROJECT_NUMBER_REGEX = r"^\d{2}\-[1-3]{3}-\d{2}([:;]\d{2})?$"


class ProjectBase(BaseModel):
    name: str
    project_number: str = Field(
        ...,
        pattern=PROJECT_NUMBER_REGEX,
        description="Standard Agency Project Number Format (YY-Type-ID[:Sub])",
    )


class ProjectCreate(ProjectBase):
    school_ids: list[int] = Field(..., min_length=1)


class Project(ProjectBase):
    id: int
    school_ids: list[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
