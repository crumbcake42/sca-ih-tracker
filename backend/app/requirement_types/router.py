from fastapi import APIRouter, Depends

from app.common.requirements import registry
from app.requirement_types.schemas import RequirementTypeInfo
from app.users.dependencies import get_current_user

router = APIRouter(
    prefix="/requirement-types",
    tags=["Requirement Types"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[RequirementTypeInfo])
async def list_requirement_types() -> list[RequirementTypeInfo]:
    result = []
    for name, handler in registry.items():
        params_model = getattr(handler, "template_params_model", None)
        result.append(
            RequirementTypeInfo(
                name=name,
                events=registry.events_for(name),
                template_params_schema=params_model.model_json_schema() if params_model else {},
                is_dismissable=getattr(handler, "is_dismissable", False),
                display_name=getattr(handler, "display_name", None),
            )
        )
    return result
