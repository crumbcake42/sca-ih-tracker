from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import PermissionName
from app.database import get_db
from app.employees.models import EmployeeRole as EmployeeRoleModel
from app.employees.models import EmployeeRoleType as EmployeeRoleTypeModel
from app.employees.schemas import (
    EmployeeRoleTypeCreate,
    EmployeeRoleTypeRead,
    EmployeeRoleTypeUpdate,
)
from app.users.dependencies import PermissionChecker, get_current_user
from app.users.models import User

router = APIRouter(prefix="/employee-role-types", tags=["Employee Role Types"])


@router.get("/", response_model=list[EmployeeRoleTypeRead])
async def list_employee_role_types(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmployeeRoleTypeModel).order_by(EmployeeRoleTypeModel.name)
    )
    return result.scalars().all()


@router.post("/", response_model=EmployeeRoleTypeRead, status_code=201)
async def create_employee_role_type(
    data: EmployeeRoleTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    existing = (
        await db.execute(
            select(EmployeeRoleTypeModel).where(EmployeeRoleTypeModel.name == data.name)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409, detail="A role type with this name already exists."
        )

    role_type = EmployeeRoleTypeModel(
        **data.model_dump(), created_by_id=current_user.id
    )
    db.add(role_type)
    await db.commit()
    await db.refresh(role_type)
    return role_type


@router.get("/{role_type_id}", response_model=EmployeeRoleTypeRead)
async def get_employee_role_type(
    role_type_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmployeeRoleTypeModel).where(EmployeeRoleTypeModel.id == role_type_id)
    )
    role_type = result.scalar_one_or_none()
    if not role_type:
        raise HTTPException(status_code=404, detail="Role type not found")
    return role_type


@router.patch("/{role_type_id}", response_model=EmployeeRoleTypeRead)
async def update_employee_role_type(
    role_type_id: int,
    data: EmployeeRoleTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    result = await db.execute(
        select(EmployeeRoleTypeModel).where(EmployeeRoleTypeModel.id == role_type_id)
    )
    role_type = result.scalar_one_or_none()
    if not role_type:
        raise HTTPException(status_code=404, detail="Role type not found")

    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        clash = (
            await db.execute(
                select(EmployeeRoleTypeModel).where(
                    EmployeeRoleTypeModel.name == update_data["name"],
                    EmployeeRoleTypeModel.id != role_type_id,
                )
            )
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(
                status_code=409, detail="A role type with this name already exists."
            )

    for field, value in update_data.items():
        setattr(role_type, field, value)
    role_type.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(role_type)
    return role_type


@router.delete("/{role_type_id}", status_code=204)
async def delete_employee_role_type(
    role_type_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    result = await db.execute(
        select(EmployeeRoleTypeModel).where(EmployeeRoleTypeModel.id == role_type_id)
    )
    role_type = result.scalar_one_or_none()
    if not role_type:
        raise HTTPException(status_code=404, detail="Role type not found")

    in_use = (
        await db.execute(
            select(EmployeeRoleModel)
            .where(EmployeeRoleModel.role_type_id == role_type_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a role type that is assigned to employee roles.",
        )

    await db.delete(role_type)
    await db.commit()
