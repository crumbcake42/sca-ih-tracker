import itertools
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import RFAStatus, WACodeStatus
from app.projects.models import Project
from app.schools.models import School
from app.wa_codes.models import WACode
from app.work_auths.models import (
    RFA,
    WorkAuth,
    WorkAuthBuildingCode,
    WorkAuthProjectCode,
)

_wa_counter = itertools.count(1)


async def seed_work_auth(db: AsyncSession, project: Project, **overrides) -> WorkAuth:
    n = next(_wa_counter)
    wa_num = overrides.pop("wa_num", f"WA-{n:04d}")
    wa = WorkAuth(
        wa_num=wa_num,
        service_id=overrides.pop("service_id", f"SVC-{n:04d}"),
        project_num=overrides.pop("project_num", f"PN-{n:04d}"),
        initiation_date=overrides.pop("initiation_date", date(2025, 1, 1)),
        project_id=project.id,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
        **overrides,
    )
    db.add(wa)
    await db.flush()
    return wa


async def seed_work_auth_project_code(
    db: AsyncSession,
    wa: WorkAuth,
    wa_code: WACode,
    *,
    fee: str = "100.00",
    status: WACodeStatus = WACodeStatus.RFA_NEEDED,
) -> WorkAuthProjectCode:
    pc = WorkAuthProjectCode(
        work_auth_id=wa.id,
        wa_code_id=wa_code.id,
        fee=Decimal(fee),
        status=status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(pc)
    await db.flush()
    return pc


async def seed_work_auth_building_code(
    db: AsyncSession,
    wa: WorkAuth,
    wa_code: WACode,
    project: Project,
    school: School,
    *,
    budget: str = "1000.00",
    status: WACodeStatus = WACodeStatus.RFA_NEEDED,
) -> WorkAuthBuildingCode:
    bc = WorkAuthBuildingCode(
        work_auth_id=wa.id,
        wa_code_id=wa_code.id,
        project_id=project.id,
        school_id=school.id,
        budget=Decimal(budget),
        status=status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(bc)
    await db.flush()
    return bc


async def seed_rfa(
    db: AsyncSession,
    wa: WorkAuth,
    *,
    status: RFAStatus = RFAStatus.PENDING,
    notes: str | None = None,
) -> RFA:
    rfa = RFA(
        work_auth_id=wa.id,
        status=status,
        notes=notes,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(rfa)
    await db.flush()
    return rfa
