from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.employees.models import Employee as EmployeeModel
from app.employees.models import EmployeeRole as EmployeeRoleModel
from app.employees.schemas import (
    Employee,
    EmployeeRole,
    EmployeeRoleCreate,
    EmployeeRoleUpdate,
)
from app.users.dependencies import get_current_user
from app.users.models import User

router = APIRouter()


# --- Employee read endpoints ---


@router.get("/", response_model=list[Employee])
async def list_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmployeeModel).order_by(
            EmployeeModel.last_name, EmployeeModel.first_name
        )
    )
    return result.scalars().all()


@router.get("/{employee_id}", response_model=Employee)
async def get_employee(employee_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmployeeModel).where(EmployeeModel.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


# --- Employee role endpoints ---


@router.get("/{employee_id}/roles", response_model=list[EmployeeRole])
async def list_employee_roles(employee_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmployeeModel)
        .where(EmployeeModel.id == employee_id)
        .options(selectinload(EmployeeModel.roles))
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return sorted(employee.roles, key=lambda r: r.start_date)


@router.post("/{employee_id}/roles", response_model=EmployeeRole, status_code=201)
async def create_employee_role(
    employee_id: int,
    data: EmployeeRoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify employee exists
    emp_result = await db.execute(
        select(EmployeeModel).where(EmployeeModel.id == employee_id)
    )
    if not emp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Employee not found")

    # Overlap check: no two roles of the same type can cover the same day
    overlap_stmt = select(EmployeeRoleModel).where(
        and_(
            EmployeeRoleModel.employee_id == employee_id,
            EmployeeRoleModel.role_type == data.role_type,
            EmployeeRoleModel.start_date
            <= (data.end_date or data.start_date.replace(year=9999)),
            (EmployeeRoleModel.end_date == None)  # noqa: E711
            | (EmployeeRoleModel.end_date >= data.start_date),
        )
    )
    overlap = (await db.execute(overlap_stmt)).scalar_one_or_none()
    if overlap:
        raise HTTPException(
            status_code=409,
            detail=f"Overlapping {data.role_type} role already exists for this employee.",
        )

    new_role = EmployeeRoleModel(
        employee_id=employee_id, **data.model_dump(), created_by_id=current_user.id
    )
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)
    return new_role


@router.patch("/roles/{role_id}", response_model=EmployeeRole)
async def update_employee_role(
    role_id: int,
    data: EmployeeRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmployeeRoleModel).where(EmployeeRoleModel.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Employee role not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    role.updated_by_id = current_user.id

    if role.end_date is not None and role.end_date <= role.start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")

    await db.commit()
    await db.refresh(role)
    return role


@router.delete("/roles/{role_id}", status_code=204)
async def delete_employee_role(role_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmployeeRoleModel).where(EmployeeRoleModel.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Employee role not found")

    await db.delete(role)
    await db.commit()
