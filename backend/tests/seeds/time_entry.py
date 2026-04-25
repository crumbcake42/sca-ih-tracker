from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import TimeEntryStatus
from app.employees.models import Employee, EmployeeRole
from app.projects.models import Project
from app.schools.models import School
from app.time_entries.models import TimeEntry

DT_START = datetime(2025, 11, 30, 17, 0, 0)
DT_END = datetime(2025, 11, 30, 21, 0, 0)


async def seed_time_entry(
    db: AsyncSession,
    employee: Employee,
    role: EmployeeRole,
    project: Project,
    school: School,
    *,
    start: datetime = DT_START,
    end: datetime | None = DT_END,
    status: TimeEntryStatus = TimeEntryStatus.ENTERED,
) -> TimeEntry:
    entry = TimeEntry(
        start_datetime=start,
        end_datetime=end,
        employee_id=employee.id,
        employee_role_id=role.id,
        project_id=project.id,
        school_id=school.id,
        status=status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(entry)
    await db.flush()
    return entry
