from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.employees.models import EmployeeRole
from app.time_entries.models import TimeEntry


async def validate_role_for_entry(
    employee_id: int,
    employee_role_id: int,
    start_datetime: datetime,
    db: AsyncSession,
) -> EmployeeRole:
    """
    Verify:
    1. The role exists.
    2. The role belongs to the given employee.
    3. The role was active on start_datetime.date().
    """
    role = await db.get(EmployeeRole, employee_role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Employee role not found")

    if role.employee_id != employee_id:
        raise HTTPException(
            status_code=422, detail="Employee role does not belong to this employee"
        )

    entry_date = start_datetime.date()
    if entry_date < role.start_date:
        raise HTTPException(
            status_code=422,
            detail=f"Role was not yet active on {entry_date} (starts {role.start_date})",
        )
    if role.end_date is not None and entry_date > role.end_date:
        raise HTTPException(
            status_code=422,
            detail=f"Role expired before {entry_date} (ended {role.end_date})",
        )

    return role


async def check_time_entry_overlap(
    employee_id: int,
    start_dt: datetime,
    end_dt: datetime | None,
    db: AsyncSession,
    exclude_id: int | None = None,
) -> None:
    """Raise 422 if the given time span overlaps any existing entry for the employee.

    NULL end_datetime (assumed entries) is always stored with start_datetime at
    midnight 00:00:00, so effective_end = start + 1 day = midnight of the next day.
    The same rule applies to the existing entries' NULL end_datetime via
    SQLite's datetime(start_datetime, '+1 day').
    """
    effective_new_end = (
        end_dt if end_dt is not None
        else start_dt + timedelta(days=1)
    )

    stmt = select(TimeEntry).where(
        TimeEntry.employee_id == employee_id,
        TimeEntry.start_datetime < effective_new_end,
        func.coalesce(
            TimeEntry.end_datetime,
            func.datetime(TimeEntry.start_datetime, "+1 day"),
        ) > start_dt,
    )
    if exclude_id is not None:
        stmt = stmt.where(TimeEntry.id != exclude_id)

    result = await db.execute(stmt)
    conflict = result.scalars().first()
    if conflict:
        raise HTTPException(
            status_code=422,
            detail=f"Time entry overlaps with existing entry {conflict.id} for this employee.",
        )


async def validate_school_on_project(
    project_id: int, school_id: int, db: AsyncSession
) -> None:
    result = await db.execute(
        text(
            "SELECT 1 FROM project_school_links "
            "WHERE project_id = :pid AND school_id = :sid"
        ),
        {"pid": project_id, "sid": school_id},
    )
    if not result.fetchone():
        raise HTTPException(
            status_code=422, detail="School is not linked to this project"
        )
