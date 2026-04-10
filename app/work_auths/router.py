from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WACodeLevel
from app.database import get_db
from app.projects.models import Project
from app.users.dependencies import PermissionChecker, PermissionName
from app.wa_codes.models import WACode
from app.work_auths import models, schemas

router = APIRouter(prefix="/work-auths", tags=["Work Auths"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_work_auth_or_404(work_auth_id: int, db: AsyncSession) -> models.WorkAuth:
    wa = await db.get(models.WorkAuth, work_auth_id)
    if not wa:
        raise HTTPException(status_code=404, detail="Work auth not found")
    return wa


async def _get_project_code_or_404(
    work_auth_id: int, wa_code_id: int, db: AsyncSession
) -> models.WorkAuthProjectCode:
    pc = await db.get(models.WorkAuthProjectCode, (work_auth_id, wa_code_id))
    if not pc:
        raise HTTPException(status_code=404, detail="Project code not found")
    return pc


async def _get_building_code_or_404(
    work_auth_id: int, wa_code_id: int, school_id: int, db: AsyncSession
) -> models.WorkAuthBuildingCode:
    # project_id is derived from the work auth
    wa = await _get_work_auth_or_404(work_auth_id, db)
    bc = await db.get(
        models.WorkAuthBuildingCode, (work_auth_id, wa_code_id, wa.project_id, school_id)
    )
    if not bc:
        raise HTTPException(status_code=404, detail="Building code not found")
    return bc


# ---------------------------------------------------------------------------
# Work Auth CRUD
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Project Codes  —  GET /work-auths/{id}/project-codes
# ---------------------------------------------------------------------------


@router.get(
    "/{work_auth_id}/project-codes",
    response_model=list[schemas.WorkAuthProjectCode],
)
async def list_project_codes(
    work_auth_id: int,
    db: AsyncSession = Depends(get_db),
):
    await _get_work_auth_or_404(work_auth_id, db)
    result = await db.execute(
        select(models.WorkAuthProjectCode).where(
            models.WorkAuthProjectCode.work_auth_id == work_auth_id
        )
    )
    return result.scalars().all()


@router.post(
    "/{work_auth_id}/project-codes",
    response_model=schemas.WorkAuthProjectCode,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def add_project_code(
    work_auth_id: int,
    body: schemas.WorkAuthProjectCodeCreate,
    db: AsyncSession = Depends(get_db),
):
    await _get_work_auth_or_404(work_auth_id, db)

    wa_code = await db.get(WACode, body.wa_code_id)
    if not wa_code:
        raise HTTPException(status_code=404, detail="WA code not found")
    if wa_code.level != WACodeLevel.PROJECT:
        raise HTTPException(
            status_code=422,
            detail=f"WA code '{wa_code.code}' is building-level and cannot be added as a project code.",
        )

    existing = await db.get(models.WorkAuthProjectCode, (work_auth_id, body.wa_code_id))
    if existing:
        raise HTTPException(status_code=409, detail="This WA code is already on the work auth.")

    pc = models.WorkAuthProjectCode(
        work_auth_id=work_auth_id,
        wa_code_id=body.wa_code_id,
        fee=body.fee,
        status=body.status,
    )
    db.add(pc)
    await db.commit()
    await db.refresh(pc)
    return pc


@router.patch(
    "/{work_auth_id}/project-codes/{wa_code_id}",
    response_model=schemas.WorkAuthProjectCode,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def update_project_code(
    work_auth_id: int,
    wa_code_id: int,
    body: schemas.WorkAuthProjectCodeUpdate,
    db: AsyncSession = Depends(get_db),
):
    pc = await _get_project_code_or_404(work_auth_id, wa_code_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pc, field, value)
    await db.commit()
    await db.refresh(pc)
    return pc


@router.delete(
    "/{work_auth_id}/project-codes/{wa_code_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def delete_project_code(
    work_auth_id: int,
    wa_code_id: int,
    db: AsyncSession = Depends(get_db),
):
    pc = await _get_project_code_or_404(work_auth_id, wa_code_id, db)
    await db.delete(pc)
    await db.commit()


# ---------------------------------------------------------------------------
# Building Codes  —  GET /work-auths/{id}/building-codes
# ---------------------------------------------------------------------------


@router.get(
    "/{work_auth_id}/building-codes",
    response_model=list[schemas.WorkAuthBuildingCode],
)
async def list_building_codes(
    work_auth_id: int,
    db: AsyncSession = Depends(get_db),
):
    await _get_work_auth_or_404(work_auth_id, db)
    result = await db.execute(
        select(models.WorkAuthBuildingCode).where(
            models.WorkAuthBuildingCode.work_auth_id == work_auth_id
        )
    )
    return result.scalars().all()


@router.post(
    "/{work_auth_id}/building-codes",
    response_model=schemas.WorkAuthBuildingCode,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def add_building_code(
    work_auth_id: int,
    body: schemas.WorkAuthBuildingCodeCreate,
    db: AsyncSession = Depends(get_db),
):
    wa = await _get_work_auth_or_404(work_auth_id, db)

    wa_code = await db.get(WACode, body.wa_code_id)
    if not wa_code:
        raise HTTPException(status_code=404, detail="WA code not found")
    if wa_code.level != WACodeLevel.BUILDING:
        raise HTTPException(
            status_code=422,
            detail=f"WA code '{wa_code.code}' is project-level and cannot be added as a building code.",
        )

    # Verify the school is linked to this project
    from sqlalchemy import text
    check = await db.execute(
        text(
            "SELECT 1 FROM project_school_links "
            "WHERE project_id = :pid AND school_id = :sid"
        ),
        {"pid": wa.project_id, "sid": body.school_id},
    )
    if not check.fetchone():
        raise HTTPException(
            status_code=422,
            detail="School is not linked to this project.",
        )

    existing = await db.get(
        models.WorkAuthBuildingCode, (work_auth_id, body.wa_code_id, wa.project_id, body.school_id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="This WA code is already on the work auth for this school.")

    bc = models.WorkAuthBuildingCode(
        work_auth_id=work_auth_id,
        wa_code_id=body.wa_code_id,
        project_id=wa.project_id,
        school_id=body.school_id,
        budget=body.budget,
        status=body.status,
    )
    db.add(bc)
    await db.commit()
    await db.refresh(bc)
    return bc


@router.patch(
    "/{work_auth_id}/building-codes/{wa_code_id}/{school_id}",
    response_model=schemas.WorkAuthBuildingCode,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def update_building_code(
    work_auth_id: int,
    wa_code_id: int,
    school_id: int,
    body: schemas.WorkAuthBuildingCodeUpdate,
    db: AsyncSession = Depends(get_db),
):
    bc = await _get_building_code_or_404(work_auth_id, wa_code_id, school_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(bc, field, value)
    await db.commit()
    await db.refresh(bc)
    return bc


@router.delete(
    "/{work_auth_id}/building-codes/{wa_code_id}/{school_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def delete_building_code(
    work_auth_id: int,
    wa_code_id: int,
    school_id: int,
    db: AsyncSession = Depends(get_db),
):
    bc = await _get_building_code_or_404(work_auth_id, wa_code_id, school_id, db)
    await db.delete(bc)
    await db.commit()
