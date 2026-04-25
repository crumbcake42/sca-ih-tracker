import itertools
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.employees.models import Employee, EmployeeRole, EmployeeRoleType

_emp_counter = itertools.count(1)
_role_type_counter = itertools.count(1)


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


async def seed_role_type(
    db: AsyncSession, *, name: str | None = None
) -> EmployeeRoleType:
    n = next(_role_type_counter)
    rt = EmployeeRoleType(name=name or f"Test Role Type {n}")
    db.add(rt)
    await db.flush()
    return rt


async def seed_employee_role(
    db: AsyncSession,
    employee: Employee,
    *,
    role_type: EmployeeRoleType | None = None,
    start: date = date(2025, 1, 1),
    end: date | None = None,
    hourly_rate: str = "75.00",
) -> EmployeeRole:
    if role_type is None:
        role_type = await seed_role_type(db)
    role = EmployeeRole(
        employee_id=employee.id,
        role_type_id=role_type.id,
        start_date=start,
        end_date=end,
        hourly_rate=hourly_rate,
    )
    db.add(role)
    await db.flush()
    return role
