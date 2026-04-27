from sqlalchemy.ext.asyncio import AsyncSession

from app.project_requirements.registry import registry
from app.project_requirements.schemas import UnfulfilledRequirement


async def get_unfulfilled_requirements_for_project(
    project_id: int,
    db: AsyncSession,
) -> list[UnfulfilledRequirement]:
    """
    Return all unfulfilled, non-dismissed requirements for a project.

    Walks every registered handler class and calls ``get_unfulfilled_for_project``.
    Dismissed requirements are skipped so the caller sees only actionable items.
    """
    out: list[UnfulfilledRequirement] = []
    for handler_cls in registry.all_handlers():
        for req in await handler_cls.get_unfulfilled_for_project(project_id, db):
            if req.is_dismissed:
                continue
            out.append(
                UnfulfilledRequirement(
                    requirement_type=req.requirement_type,
                    project_id=req.project_id,
                    requirement_key=req.requirement_key,
                    label=req.label,
                    is_dismissed=req.is_dismissed,
                    is_dismissable=req.is_dismissable,
                )
            )
    return out
