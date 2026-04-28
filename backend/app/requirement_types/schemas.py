from pydantic import BaseModel

from app.common.enums import RequirementEvent


class RequirementTypeInfo(BaseModel):
    name: str
    events: list[RequirementEvent]
    template_params_schema: dict
    is_dismissable: bool
    display_name: str | None = None
