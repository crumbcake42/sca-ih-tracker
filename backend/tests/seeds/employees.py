import itertools
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import EmployeeRoleType
from app.employees.models import Employee, EmployeeRole

_emp_counter = itertools.count(1)


async def seed_employee(db: AsyncSession, **overrides) -> Employee:
    n = next(_emp_counter)
    first = overrides.pop("first_name", "Jane")
    last = overrides.pop("last_name", "Doe")
    emp = Employee(
        first_name=first,
        last_name=last,
        display_name=overrides.pop("display_name", f"{first} {last} {n}"),
        **overrides,
    )
    db.add(emp)
    await db.flush()
    return emp


async def seed_employee_role(
    db: AsyncSession,
    employee: Employee,
    *,
    role_type: EmployeeRoleType = EmployeeRoleType.ACM_AIR_TECH,
    start_date: date = date(2025, 1, 1),
    end_date: date | None = None,
    hourly_rate: str = "75.00",
) -> EmployeeRole:
    role = EmployeeRole(
        employee_id=employee.id,
        role_type=role_type,
        start_date=start_date,
        end_date=end_date,
        hourly_rate=hourly_rate,
    )
    db.add(role)
    await db.flush()
    return role
