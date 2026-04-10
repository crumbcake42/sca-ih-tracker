from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.work_auths import models


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
        models.WorkAuthBuildingCode,
        (work_auth_id, wa_code_id, wa.project_id, school_id),
    )
    if not bc:
        raise HTTPException(status_code=404, detail="Building code not found")
    return bc
