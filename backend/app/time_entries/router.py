from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import SampleBatchStatus, TimeEntryStatus
from app.database import get_db
from app.employees.models import Employee
from app.lab_results.models import SampleBatch
from app.projects.models import Project
from app.projects.services import ensure_deliverables_exist, recalculate_deliverable_sca_status
from app.time_entries.models import TimeEntry
from app.time_entries.schemas import TimeEntryCreate, TimeEntryRead, TimeEntryUpdate
from app.time_entries.service import (
    check_time_entry_overlap,
    validate_role_for_entry,
    validate_school_on_project,
)
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter(prefix="/time-entries", tags=["time-entries"])


@router.get("/", response_model=list[TimeEntryRead])
async def list_time_entries(
    project_id: int | None = Query(None),
    school_id: int | None = Query(None),
    employee_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TimeEntry)
    if project_id is not None:
        stmt = stmt.where(TimeEntry.project_id == project_id)
    if school_id is not None:
        stmt = stmt.where(TimeEntry.school_id == school_id)
    if employee_id is not None:
        stmt = stmt.where(TimeEntry.employee_id == employee_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{entry_id}", response_model=TimeEntryRead)
async def get_time_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    entry = await db.get(TimeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return entry


@router.post(
    "/",
    response_model=TimeEntryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_time_entry(
    body: TimeEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    # Verify employee exists
    employee = await db.get(Employee, body.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Verify project exists
    project = await db.get(Project, body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify school is linked to project
    await validate_school_on_project(body.project_id, body.school_id, db)

    # Verify role belongs to employee and was active on entry date
    await validate_role_for_entry(
        body.employee_id, body.employee_role_id, body.start_datetime, db
    )

    # Verify no overlapping entry exists for this employee
    await check_time_entry_overlap(
        body.employee_id, body.start_datetime, body.end_datetime, db
    )

    entry = TimeEntry(
        start_datetime=body.start_datetime,
        end_datetime=body.end_datetime,
        employee_id=body.employee_id,
        employee_role_id=body.employee_role_id,
        project_id=body.project_id,
        school_id=body.school_id,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(entry)
    await db.flush()
    await ensure_deliverables_exist(body.project_id, db)
    await recalculate_deliverable_sca_status(body.project_id, db)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.patch(
    "/{entry_id}",
    response_model=TimeEntryRead,
)
async def update_time_entry(
    entry_id: int,
    body: TimeEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    entry = await db.get(TimeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    updates = body.model_dump(exclude_unset=True)

    # If start_datetime is changing, re-validate the role against the new date
    new_start = updates.get("start_datetime", entry.start_datetime)
    if "start_datetime" in updates:
        await validate_role_for_entry(
            entry.employee_id, entry.employee_role_id, new_start, db
        )

    # If only end_datetime is being set, verify it's still after start
    if "end_datetime" in updates and "start_datetime" not in updates:
        new_end = updates["end_datetime"]
        if new_end is not None and new_end <= entry.start_datetime:
            raise HTTPException(
                status_code=422,
                detail="end_datetime must be after start_datetime",
            )

    # Verify no overlapping entry exists for this employee after applying updates
    effective_start = updates.get("start_datetime", entry.start_datetime)
    effective_end = updates.get("end_datetime", entry.end_datetime)
    await check_time_entry_overlap(
        entry.employee_id, effective_start, effective_end, db, exclude_id=entry.id
    )

    for field, value in updates.items():
        setattr(entry, field, value)

    # Any manager edit on an assumed entry promotes it to entered
    if entry.status == TimeEntryStatus.ASSUMED:
        entry.status = TimeEntryStatus.ENTERED

    entry.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
async def delete_time_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    entry = await db.get(TimeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    # Block deletion if active or discarded batches are linked
    result = await db.execute(
        select(func.count()).select_from(SampleBatch).where(
            SampleBatch.time_entry_id == entry_id,
            SampleBatch.status.in_([SampleBatchStatus.ACTIVE, SampleBatchStatus.DISCARDED]),
        )
    )
    if result.scalar() > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: time entry has linked batches. Reassign or delete them first.",
        )

    await db.delete(entry)
    await db.commit()
