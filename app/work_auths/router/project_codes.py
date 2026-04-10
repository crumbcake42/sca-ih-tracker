from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WACodeLevel
from app.database import get_db
from app.users.dependencies import PermissionChecker, PermissionName
from app.wa_codes.models import WACode
from app.work_auths import models, schemas

from ._helpers import _get_work_auth_or_404, _get_project_code_or_404

router = APIRouter(
    prefix="/{work_auth_id}/project-codes", tags=["Work Auth Project Codes"]
)

# ---------------------------------------------------------------------------
# Project Codes  —  GET /work-auths/{id}/project-codes
# ---------------------------------------------------------------------------


@router.get(
    "",
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
    "",
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
        raise HTTPException(
            status_code=409, detail="This WA code is already on the work auth."
        )

    fee = body.fee if body.fee is not None else wa_code.default_fee
    if fee is None:
        raise HTTPException(
            status_code=422,
            detail="Fee is required — no fee provided and this WA code has no default fee.",
        )

    pc = models.WorkAuthProjectCode(
        work_auth_id=work_auth_id,
        wa_code_id=body.wa_code_id,
        fee=fee,
        status=body.status,
    )
    db.add(pc)
    await db.commit()
    await db.refresh(pc)
    return pc


@router.patch(
    "/{wa_code_id}",
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
    "/{wa_code_id}",
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
