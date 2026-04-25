import itertools

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import SCADeliverableStatus, WACodeLevel
from app.deliverables.models import (
    Deliverable,
    DeliverableWACodeTrigger,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.projects.models import Project
from app.schools.models import School
from app.wa_codes.models import WACode

_counter = itertools.count(1)


async def seed_deliverable(
    db: AsyncSession,
    *,
    name: str | None = None,
    level: WACodeLevel = WACodeLevel.PROJECT,
) -> Deliverable:
    n = next(_counter)
    deliv = Deliverable(
        name=name or f"Test Report {n}",
        level=level,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(deliv)
    await db.flush()
    return deliv


async def seed_deliverable_with_trigger(
    db: AsyncSession,
    wa_code: WACode,
    *,
    name: str | None = None,
    level: WACodeLevel = WACodeLevel.PROJECT,
) -> Deliverable:
    n = next(_counter)
    deliv = Deliverable(
        name=name or f"Test Report {n}",
        level=level,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(deliv)
    await db.flush()
    db.add(DeliverableWACodeTrigger(deliverable_id=deliv.id, wa_code_id=wa_code.id))
    await db.flush()
    return deliv


async def seed_project_deliverable(
    db: AsyncSession,
    project: Project,
    deliverable: Deliverable,
    *,
    sca_status: SCADeliverableStatus = SCADeliverableStatus.PENDING_WA,
) -> ProjectDeliverable:
    pd = ProjectDeliverable(
        project_id=project.id,
        deliverable_id=deliverable.id,
        sca_status=sca_status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(pd)
    await db.flush()
    return pd


async def seed_project_building_deliverable(
    db: AsyncSession,
    project: Project,
    deliverable: Deliverable,
    school: School,
    *,
    sca_status: SCADeliverableStatus = SCADeliverableStatus.PENDING_WA,
) -> ProjectBuildingDeliverable:
    pbd = ProjectBuildingDeliverable(
        project_id=project.id,
        deliverable_id=deliverable.id,
        school_id=school.id,
        sca_status=sca_status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(pbd)
    await db.flush()
    return pbd
