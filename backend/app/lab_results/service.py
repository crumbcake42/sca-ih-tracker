from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import RequirementEvent, TimeEntryStatus
from app.common.requirements.dispatcher import dispatch_requirement_event
from app.employees.models import Employee, EmployeeRole
from app.lab_results.models import (
    SampleBatch,
    SampleBatchInspector,
    SampleBatchUnit,
    SampleType,
    SampleTypeRequiredRole,
    SampleUnitType,
    TurnaroundOption,
)
from app.projects.models import Project
from app.time_entries.models import TimeEntry
from app.time_entries.service import (
    check_time_entry_overlap,
    validate_role_for_entry,
    validate_school_on_project,
)

if TYPE_CHECKING:
    from app.lab_results.schemas import QuickAddBatchCreate

async def get_sample_type_or_404(sample_type_id: int, db: AsyncSession) -> SampleType:
    # Use select() with populate_existing=True rather than db.get() so that:
    # 1. lazy="selectin" relationships are loaded in the same greenlet context
    #    (db.get() may return a cached identity-map instance with unloaded
    #    collections, which fails on serialization outside a greenlet).
    # 2. populate_existing forces a re-query even when the object is already in
    #    the identity map, ensuring child collections added after the initial
    #    load (e.g., subtypes, unit types) are reflected in the response.
    result = await db.execute(
        select(SampleType)
        .where(SampleType.id == sample_type_id)
        .execution_options(populate_existing=True)
    )
    st = result.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Sample type not found")
    return st


async def get_batch_or_404(batch_id: int, db: AsyncSession) -> SampleBatch:
    batch = await db.get(SampleBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Sample batch not found")
    return batch


async def validate_unit_types_for_batch(
    sample_type_id: int,
    unit_type_ids: list[int],
    db: AsyncSession,
) -> None:
    """All unit types submitted must belong to the batch's sample type."""
    if not unit_type_ids:
        return
    result = await db.execute(
        select(SampleUnitType).where(SampleUnitType.id.in_(unit_type_ids))
    )
    unit_types = result.scalars().all()

    missing = set(unit_type_ids) - {ut.id for ut in unit_types}
    if missing:
        raise HTTPException(status_code=404, detail=f"Unit type(s) not found: {missing}")

    wrong_type = [ut for ut in unit_types if ut.sample_type_id != sample_type_id]
    if wrong_type:
        names = [ut.name for ut in wrong_type]
        raise HTTPException(
            status_code=422,
            detail=f"Unit type(s) {names} do not belong to the selected sample type",
        )


async def validate_turnaround_for_batch(
    sample_type_id: int,
    turnaround_option_id: int,
    db: AsyncSession,
) -> None:
    """TAT option must belong to the batch's sample type."""
    tat = await db.get(TurnaroundOption, turnaround_option_id)
    if not tat:
        raise HTTPException(status_code=404, detail="Turnaround option not found")
    if tat.sample_type_id != sample_type_id:
        raise HTTPException(
            status_code=422,
            detail="Turnaround option does not belong to the selected sample type",
        )


async def validate_subtype_for_batch(
    sample_type_id: int,
    sample_subtype_id: int,
    db: AsyncSession,
) -> None:
    """Subtype must belong to the batch's sample type."""
    from app.lab_results.models import SampleSubtype
    subtype = await db.get(SampleSubtype, sample_subtype_id)
    if not subtype:
        raise HTTPException(status_code=404, detail="Sample subtype not found")
    if subtype.sample_type_id != sample_type_id:
        raise HTTPException(
            status_code=422,
            detail="Sample subtype does not belong to the selected sample type",
        )


async def validate_employee_role_for_sample_type(
    time_entry_id: int | None,
    sample_type_id: int,
    db: AsyncSession,
) -> None:
    """If the sample type defines required roles, the employee's role on the linked
    time entry must match at least one of them. No required roles = no restriction.
    If time_entry_id is None (batch not linked to a time entry), skip role validation."""
    required_result = await db.execute(
        select(SampleTypeRequiredRole).where(
            SampleTypeRequiredRole.sample_type_id == sample_type_id
        )
    )
    required = required_result.scalars().all()
    if not required:
        return  # no restriction

    if time_entry_id is None:
        return  # no time entry to check against; role validation deferred

    time_entry = await db.get(TimeEntry, time_entry_id)
    if not time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    employee_role = await db.get(EmployeeRole, time_entry.employee_role_id)
    if not employee_role:
        raise HTTPException(status_code=404, detail="Employee role not found")

    allowed_role_types = {r.role_type for r in required}
    if employee_role.role_type not in allowed_role_types:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Employee role '{employee_role.role_type}' is not permitted to collect "
                f"this sample type. Required: {[r.value for r in allowed_role_types]}"
            ),
        )


async def validate_inspector_count(
    sample_type: SampleType,
    inspector_count: int,
) -> None:
    if not sample_type.allows_multiple_inspectors and inspector_count > 1:
        raise HTTPException(
            status_code=422,
            detail=f"Sample type '{sample_type.name}' only allows one inspector per batch",
        )


async def quick_add_batch(
    body: "QuickAddBatchCreate",
    db: AsyncSession,
) -> SampleBatch:
    """Atomically create an assumed TimeEntry and a linked SampleBatch.

    The time entry is created with status=assumed, start_datetime=midnight of
    body.date_on_site, end_datetime=None, and created_by_id=SYSTEM_USER_ID.
    All validations run before any DB writes; on failure the transaction rolls back.
    """


    # --- Time entry validations ---
    if not await db.get(Employee, body.employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    if not await db.get(Project, body.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    await validate_school_on_project(body.project_id, body.school_id, db)

    start_dt = datetime(body.date_on_site.year, body.date_on_site.month, body.date_on_site.day)
    await validate_role_for_entry(body.employee_id, body.employee_role_id, start_dt, db)
    await check_time_entry_overlap(body.employee_id, start_dt, None, db)

    # --- Batch validations ---
    sample_type = await get_sample_type_or_404(body.sample_type_id, db)

    existing = await db.execute(
        select(SampleBatch).where(SampleBatch.batch_num == body.batch_num)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Batch number already exists")

    if body.sample_subtype_id is not None:
        await validate_subtype_for_batch(body.sample_type_id, body.sample_subtype_id, db)
    if body.turnaround_option_id is not None:
        await validate_turnaround_for_batch(body.sample_type_id, body.turnaround_option_id, db)

    unit_type_ids = [u.sample_unit_type_id for u in body.units]
    await validate_unit_types_for_batch(body.sample_type_id, unit_type_ids, db)
    await validate_inspector_count(sample_type, len(body.inspector_ids))

    for emp_id in body.inspector_ids:
        if not await db.get(Employee, emp_id):
            raise HTTPException(status_code=404, detail=f"Employee {emp_id} not found")

    # --- Writes (all-or-nothing) ---
    entry = TimeEntry(
        start_datetime=start_dt,
        end_datetime=None,
        employee_id=body.employee_id,
        employee_role_id=body.employee_role_id,
        project_id=body.project_id,
        school_id=body.school_id,
        status=TimeEntryStatus.ASSUMED,
        created_by_id=SYSTEM_USER_ID,
    )
    db.add(entry)
    await db.flush()  # get entry.id before creating the batch

    # Validate employee role for sample type using the new time entry
    await validate_employee_role_for_sample_type(entry.id, body.sample_type_id, db)

    batch = SampleBatch(
        sample_type_id=body.sample_type_id,
        sample_subtype_id=body.sample_subtype_id,
        turnaround_option_id=body.turnaround_option_id,
        time_entry_id=entry.id,
        batch_num=body.batch_num,
        is_report=body.is_report,
        date_collected=body.date_collected,
        notes=body.notes,
        created_by_id=SYSTEM_USER_ID,
    )
    db.add(batch)
    await db.flush()

    for unit in body.units:
        db.add(SampleBatchUnit(
            batch_id=batch.id,
            sample_unit_type_id=unit.sample_unit_type_id,
            quantity=unit.quantity,
        ))

    for emp_id in body.inspector_ids:
        db.add(SampleBatchInspector(batch_id=batch.id, employee_id=emp_id))

    await dispatch_requirement_event(
        project_id=entry.project_id,
        event=RequirementEvent.TIME_ENTRY_CREATED,
        payload={"time_entry_id": entry.id},
        db=db,
    )
    await db.commit()
    await db.refresh(batch)
    return batch
