from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.employees.models import EmployeeRole


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
