from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RFAAction, RFAStatus, WACodeStatus
from app.database import get_db
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User
from app.work_auths import models, schemas

from ._helpers import _get_work_auth_or_404

router = APIRouter(prefix="/{wa_id}/rfas", tags=["RFAs"])


async def _get_rfa_or_404(rfa_id: int, work_auth_id: int, db: AsyncSession) -> models.RFA:
    result = await db.execute(
        select(models.RFA).where(
            models.RFA.id == rfa_id,
            models.RFA.work_auth_id == work_auth_id,
        )
    )
    rfa = result.scalar_one_or_none()
    if not rfa:
        raise HTTPException(status_code=404, detail="RFA not found")
    return rfa


# ---------------------------------------------------------------------------
# POST /work-auths/{wa_id}/rfas
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=schemas.RFA,
    status_code=status.HTTP_201_CREATED,
)
async def create_rfa(
    wa_id: int,
    body: schemas.RFACreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    wa = await _get_work_auth_or_404(wa_id, db)

    # Enforce one-pending-per-work-auth
    existing_pending = await db.execute(
        select(models.RFA).where(
            models.RFA.work_auth_id == wa.id,
            models.RFA.status == RFAStatus.PENDING,
        )
    )
    if existing_pending.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="This work auth already has a pending RFA.",
        )

    rfa = models.RFA(
        work_auth_id=wa.id,
        status=RFAStatus.PENDING,
        submitted_by_id=body.submitted_by_id,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(rfa)
    await db.flush()  # get rfa.id before creating child rows

    # Create project code rows and mark referenced codes as RFA_PENDING
    for pc in body.project_codes:
        db.add(models.RFAProjectCode(
            rfa_id=rfa.id,
            wa_code_id=pc.wa_code_id,
            action=pc.action,
        ))
        wapc = await db.get(
            models.WorkAuthProjectCode,
            {"work_auth_id": wa.id, "wa_code_id": pc.wa_code_id},
        )
        if wapc:
            wapc.status = WACodeStatus.RFA_PENDING

    # Create building code rows and mark referenced codes as RFA_PENDING
    for bc in body.building_codes:
        db.add(models.RFABuildingCode(
            rfa_id=rfa.id,
            wa_code_id=bc.wa_code_id,
            project_id=wa.project_id,
            school_id=bc.school_id,
            action=bc.action,
            budget_adjustment=bc.budget_adjustment,
        ))
        wabc = await db.get(
            models.WorkAuthBuildingCode,
            {
                "work_auth_id": wa.id,
                "wa_code_id": bc.wa_code_id,
                "project_id": wa.project_id,
                "school_id": bc.school_id,
            },
        )
        if wabc:
            wabc.status = WACodeStatus.RFA_PENDING

    await db.commit()
    await db.refresh(rfa)
    return rfa


# ---------------------------------------------------------------------------
# GET /work-auths/{wa_id}/rfas
# ---------------------------------------------------------------------------


@router.get("", response_model=list[schemas.RFA])
async def list_rfas(
    wa_id: int,
    db: AsyncSession = Depends(get_db),
):
    await _get_work_auth_or_404(wa_id, db)

    result = await db.execute(
        select(models.RFA)
        .where(models.RFA.work_auth_id == wa_id)
        .order_by(models.RFA.submitted_at)
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# PATCH /work-auths/{wa_id}/rfas/{rfa_id}
# ---------------------------------------------------------------------------


@router.patch(
    "/{rfa_id}",
    response_model=schemas.RFA,
)
async def resolve_rfa(
    wa_id: int,
    rfa_id: int,
    body: schemas.RFAResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    await _get_work_auth_or_404(wa_id, db)
    rfa = await _get_rfa_or_404(rfa_id, wa_id, db)

    if rfa.status != RFAStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"RFA is already {rfa.status} and cannot be resolved again.",
        )

    if body.status == RFAStatus.PENDING:
        raise HTTPException(
            status_code=422,
            detail="Cannot resolve an RFA to 'pending'.",
        )

    # Load child rows (already in session from relationships after refresh,
    # but we query explicitly to avoid lazy-load issues with async)
    pc_result = await db.execute(
        select(models.RFAProjectCode).where(models.RFAProjectCode.rfa_id == rfa.id)
    )
    rfa_project_codes = pc_result.scalars().all()

    bc_result = await db.execute(
        select(models.RFABuildingCode).where(models.RFABuildingCode.rfa_id == rfa.id)
    )
    rfa_building_codes = bc_result.scalars().all()

    if body.status == RFAStatus.APPROVED:
        for rfa_pc in rfa_project_codes:
            wapc = await db.get(
                models.WorkAuthProjectCode,
                {"work_auth_id": wa_id, "wa_code_id": rfa_pc.wa_code_id},
            )
            if wapc:
                wapc.status = (
                    WACodeStatus.ADDED_BY_RFA
                    if rfa_pc.action == RFAAction.ADD
                    else WACodeStatus.REMOVED
                )

        for rfa_bc in rfa_building_codes:
            wabc = await db.get(
                models.WorkAuthBuildingCode,
                {
                    "work_auth_id": wa_id,
                    "wa_code_id": rfa_bc.wa_code_id,
                    "project_id": rfa_bc.project_id,
                    "school_id": rfa_bc.school_id,
                },
            )
            if wabc:
                wabc.status = (
                    WACodeStatus.ADDED_BY_RFA
                    if rfa_bc.action == RFAAction.ADD
                    else WACodeStatus.REMOVED
                )
                if rfa_bc.budget_adjustment is not None:
                    from decimal import Decimal
                    wabc.budget = Decimal(str(wabc.budget)) + rfa_bc.budget_adjustment

    else:
        # rejected or withdrawn — revert codes to RFA_NEEDED
        for rfa_pc in rfa_project_codes:
            wapc = await db.get(
                models.WorkAuthProjectCode,
                {"work_auth_id": wa_id, "wa_code_id": rfa_pc.wa_code_id},
            )
            if wapc:
                wapc.status = WACodeStatus.RFA_NEEDED

        for rfa_bc in rfa_building_codes:
            wabc = await db.get(
                models.WorkAuthBuildingCode,
                {
                    "work_auth_id": wa_id,
                    "wa_code_id": rfa_bc.wa_code_id,
                    "project_id": rfa_bc.project_id,
                    "school_id": rfa_bc.school_id,
                },
            )
            if wabc:
                wabc.status = WACodeStatus.RFA_NEEDED

    rfa.status = body.status
    rfa.resolved_at = datetime.now(UTC)
    if body.notes is not None:
        rfa.notes = body.notes
    rfa.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(rfa)
    return rfa
