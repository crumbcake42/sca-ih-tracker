from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.projects.models import Project
from app.users.dependencies import PermissionChecker, PermissionName
from app.work_auths import models, schemas

router = APIRouter(prefix="/work-auths", tags=["Work Auths"])


async def _get_work_auth_or_404(work_auth_id: int, db: AsyncSession) -> models.WorkAuth:
    wa = await db.get(models.WorkAuth, work_auth_id)
    if not wa:
        raise HTTPException(status_code=404, detail="Work auth not found")
    return wa


@router.post(
    "",
    response_model=schemas.WorkAuth,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def create_work_auth(
    body: schemas.WorkAuthCreate,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = await db.execute(
        select(models.WorkAuth).where(models.WorkAuth.project_id == body.project_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A work auth already exists for this project.",
        )

    wa = models.WorkAuth(**body.model_dump())
    db.add(wa)
    await db.commit()
    await db.refresh(wa)
    return wa


@router.get("/{work_auth_id}", response_model=schemas.WorkAuth)
async def get_work_auth(
    work_auth_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await _get_work_auth_or_404(work_auth_id, db)


@router.get("", response_model=schemas.WorkAuth)
async def get_work_auth_for_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.WorkAuth).where(models.WorkAuth.project_id == project_id)
    )
    wa = result.scalar_one_or_none()
    if not wa:
        raise HTTPException(status_code=404, detail="No work auth found for this project")
    return wa


@router.patch(
    "/{work_auth_id}",
    response_model=schemas.WorkAuth,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def update_work_auth(
    work_auth_id: int,
    body: schemas.WorkAuthUpdate,
    db: AsyncSession = Depends(get_db),
):
    wa = await _get_work_auth_or_404(work_auth_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(wa, field, value)
    await db.commit()
    await db.refresh(wa)
    return wa


@router.delete(
    "/{work_auth_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def delete_work_auth(
    work_auth_id: int,
    db: AsyncSession = Depends(get_db),
):
    wa = await _get_work_auth_or_404(work_auth_id, db)
    await db.delete(wa)
    await db.commit()
