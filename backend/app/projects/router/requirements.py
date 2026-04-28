from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.requirements import UnfulfilledRequirement, get_unfulfilled_requirements_for_project
from app.database import get_db
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter(prefix="/{project_id}/requirements", tags=["Projects"])


@router.get("", response_model=list[UnfulfilledRequirement])
async def list_project_requirements(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
) -> list[UnfulfilledRequirement]:
    return await get_unfulfilled_requirements_for_project(project_id, db)
