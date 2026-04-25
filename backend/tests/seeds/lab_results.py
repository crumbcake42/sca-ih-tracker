import itertools
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import EmployeeRoleType, SampleBatchStatus
from app.lab_results.models import (
    SampleBatch,
    SampleSubtype,
    SampleType,
    SampleTypeRequiredRole,
    SampleUnitType,
    TurnaroundOption,
)
from app.time_entries.models import TimeEntry

_sample_type_counter = itertools.count(1)
_batch_counter = itertools.count(1)


async def seed_sample_type(
    db: AsyncSession,
    *,
    name: str | None = None,
    allows_multiple_inspectors: bool = True,
) -> SampleType:
    n = next(_sample_type_counter)
    st = SampleType(
        name=name or f"Test Sample Type {n}",
        allows_multiple_inspectors=allows_multiple_inspectors,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(st)
    await db.flush()
    return st


async def seed_sample_batch(
    db: AsyncSession,
    time_entry: TimeEntry,
    sample_type: SampleType,
    *,
    status: SampleBatchStatus = SampleBatchStatus.ACTIVE,
    batch_num: str | None = None,
) -> SampleBatch:
    n = next(_batch_counter)
    batch = SampleBatch(
        sample_type_id=sample_type.id,
        time_entry_id=time_entry.id,
        batch_num=batch_num or f"BATCH-{n:04d}",
        is_report=False,
        date_collected=date(2025, 6, 1),
        status=status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(batch)
    await db.flush()
    return batch


async def seed_sample_unit_type(
    db: AsyncSession, sample_type: SampleType, *, name: str = "PCM Sample"
) -> SampleUnitType:
    ut = SampleUnitType(sample_type_id=sample_type.id, name=name)
    db.add(ut)
    await db.flush()
    return ut


async def seed_sample_subtype(
    db: AsyncSession, sample_type: SampleType, *, name: str = "Friable"
) -> SampleSubtype:
    st = SampleSubtype(sample_type_id=sample_type.id, name=name)
    db.add(st)
    await db.flush()
    return st


async def seed_sample_turnaround_option(
    db: AsyncSession,
    sample_type: SampleType,
    *,
    hours: int = 24,
    label: str = "Standard",
) -> TurnaroundOption:
    tat = TurnaroundOption(sample_type_id=sample_type.id, hours=hours, label=label)
    db.add(tat)
    await db.flush()
    return tat


async def seed_required_role(
    db: AsyncSession,
    sample_type: SampleType,
    *,
    role_type: EmployeeRoleType = EmployeeRoleType.ACM_AIR_TECH,
) -> SampleTypeRequiredRole:
    rr = SampleTypeRequiredRole(sample_type_id=sample_type.id, role_type=role_type)
    db.add(rr)
    await db.flush()
    return rr
