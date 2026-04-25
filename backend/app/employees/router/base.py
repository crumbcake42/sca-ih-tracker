from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.factories import create_readonly_router
from app.common.guards import assert_deletable
from app.database import get_db
from app.employees.models import Employee as EmployeeModel
from app.employees.models import EmployeeRole as EmployeeRoleModel
from app.employees.schemas import (
    Employee,
    EmployeeCreate,
    EmployeeRole,
    EmployeeRoleCreate,
    EmployeeRoleUpdate,
    EmployeeUpdate,
)
from app.employees.service import generate_unique_display_name
from app.lab_results.models import SampleBatchInspector
from app.time_entries.models import TimeEntry
from app.users.dependencies import get_current_user
from app.users.models import User

router = APIRouter()


# --- Uniqueness helpers ---


async def _ensure_adp_id_unique(
    db: AsyncSession, adp_id: str, exclude_id: int | None = None
) -> None:
    stmt = select(EmployeeModel).where(EmployeeModel.adp_id == adp_id)
    if exclude_id is not None:
        stmt = stmt.where(EmployeeModel.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=422, detail=f"adp_id '{adp_id}' already exists.")


async def _ensure_email_unique(
    db: AsyncSession, email: str, exclude_id: int | None = None
) -> None:
    stmt = select(EmployeeModel).where(EmployeeModel.email == email)
    if exclude_id is not None:
        stmt = stmt.where(EmployeeModel.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=422, detail=f"email '{email}' already exists.")


async def _ensure_display_name_unique(
    db: AsyncSession, display_name: str, exclude_id: int | None = None
) -> None:
    stmt = select(EmployeeModel).where(EmployeeModel.display_name == display_name)
    if exclude_id is not None:
        stmt = stmt.where(EmployeeModel.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=422, detail=f"display_name '{display_name}' already exists."
        )


# --- Employee CRUD endpoints ---
router.include_router(
    create_readonly_router(
        model=EmployeeModel,
        read_schema=Employee,
        default_sort=EmployeeModel.last_name.asc(),
        search_attr=EmployeeModel.last_name,
    )
)


@router.post("/", response_model=Employee, status_code=201)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.adp_id is not None:
        await _ensure_adp_id_unique(db, data.adp_id)
    if data.email is not None:
        await _ensure_email_unique(db, data.email)

    if data.display_name is not None:
        # Explicit display_name: 422 on collision rather than auto-dedup
        await _ensure_display_name_unique(db, data.display_name)
        display_name = data.display_name
    else:
        display_name = await generate_unique_display_name(
            db, data.first_name, data.last_name
        )

    employee = EmployeeModel(
        **data.model_dump(exclude={"display_name"}),
        display_name=display_name,
        created_by_id=current_user.id,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


@router.get("/{employee_id}", response_model=Employee)
async def get_employee(employee_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmployeeModel).where(EmployeeModel.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.patch("/{employee_id}", response_model=Employee)
async def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmployeeModel).where(EmployeeModel.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    updates = data.model_dump(exclude_unset=True)

    if "adp_id" in updates and updates["adp_id"] != employee.adp_id:
        await _ensure_adp_id_unique(db, updates["adp_id"], exclude_id=employee.id)
    if "email" in updates and updates["email"] != employee.email:
        await _ensure_email_unique(db, updates["email"], exclude_id=employee.id)
    if "display_name" in updates and updates["display_name"] != employee.display_name:
        await _ensure_display_name_unique(
            db, updates["display_name"], exclude_id=employee.id
        )

    for field, value in updates.items():
        setattr(employee, field, value)
    employee.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(employee)
    return employee


# --- Employee reference / delete ---


async def _get_employee_references(db: AsyncSession, employee_id: int) -> dict[str, int]:
    time_entry_count = await db.scalar(
        select(func.count()).select_from(TimeEntry).where(TimeEntry.employee_id == employee_id)
    )
    inspector_count = await db.scalar(
        select(func.count())
        .select_from(SampleBatchInspector)
        .where(SampleBatchInspector.employee_id == employee_id)
    )
    return {"time_entries": time_entry_count or 0, "sample_batch_inspectors": inspector_count or 0}


@router.get("/{employee_id}/connections")
async def get_employee_connections(employee_id: int, db: AsyncSession = Depends(get_db)):
    employee = await db.get(EmployeeModel, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return await _get_employee_references(db, employee_id)


@router.delete("/{employee_id}", status_code=204)
async def delete_employee(employee_id: int, db: AsyncSession = Depends(get_db)):
    employee = await db.get(EmployeeModel, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    assert_deletable(await _get_employee_references(db, employee_id))
    await db.delete(employee)
    await db.commit()


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
            detail=f"Overlapping '{data.role_type.value}' role already exists for this employee.",
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
