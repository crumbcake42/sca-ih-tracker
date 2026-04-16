from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WACodeLevel
from app.database import get_db
from app.projects.services import (
    check_sample_type_gap_note,
    ensure_deliverables_exist,
    recalculate_deliverable_sca_status,
)
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User
from app.wa_codes.models import WACode
from app.work_auths import models, schemas

from ._helpers import _get_building_code_or_404, _get_work_auth_or_404

router = APIRouter(
    prefix="/{work_auth_id}/building-codes", tags=["Work Auth Building Codes"]
)

# ---------------------------------------------------------------------------
# Building Codes  —  GET /work-auths/{id}/building-codes
# ---------------------------------------------------------------------------


@router.get(
    "",
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
    "",
    response_model=schemas.WorkAuthBuildingCode,
    status_code=status.HTTP_201_CREATED,
)
async def add_building_code(
    work_auth_id: int,
    body: schemas.WorkAuthBuildingCodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
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
        models.WorkAuthBuildingCode,
        (work_auth_id, body.wa_code_id, wa.project_id, body.school_id),
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="This WA code is already on the work auth for this school.",
        )

    bc = models.WorkAuthBuildingCode(
        work_auth_id=work_auth_id,
        wa_code_id=body.wa_code_id,
        project_id=wa.project_id,
        school_id=body.school_id,
        budget=body.budget,
        status=body.status,
        created_by_id=current_user.id,
    )
    db.add(bc)
    await db.flush()
    await ensure_deliverables_exist(wa.project_id, db)
    await recalculate_deliverable_sca_status(wa.project_id, db)
    await check_sample_type_gap_note(wa.project_id, db)
    await db.commit()
    await db.refresh(bc)
    return bc


@router.patch(
    "/{wa_code_id}/{school_id}",
    response_model=schemas.WorkAuthBuildingCode,
)
async def update_building_code(
    work_auth_id: int,
    wa_code_id: int,
    school_id: int,
    body: schemas.WorkAuthBuildingCodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    bc = await _get_building_code_or_404(work_auth_id, wa_code_id, school_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(bc, field, value)
    bc.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(bc)
    return bc


@router.delete(
    "/{wa_code_id}/{school_id}",
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
    project_id = bc.project_id
    await db.delete(bc)
    await db.flush()
    await recalculate_deliverable_sca_status(project_id, db)
    await db.commit()
