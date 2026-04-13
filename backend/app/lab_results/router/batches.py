from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.employees.models import Employee
from app.lab_results.models import (
    SampleBatch,
    SampleBatchInspector,
    SampleBatchUnit,
)
from app.lab_results.schemas import (
    SampleBatchCreate,
    SampleBatchRead,
    SampleBatchUpdate,
)
from app.lab_results.service import (
    get_batch_or_404,
    get_sample_type_or_404,
    validate_employee_role_for_sample_type,
    validate_inspector_count,
    validate_subtype_for_batch,
    validate_turnaround_for_batch,
    validate_unit_types_for_batch,
)
from app.time_entries.models import TimeEntry
from app.users.dependencies import PermissionChecker, PermissionName

router = APIRouter(prefix="/batches", tags=["Lab Results — Batches"])

_edit = [Depends(PermissionChecker(PermissionName.PROJECT_EDIT))]


@router.get("/", response_model=list[SampleBatchRead])
async def list_batches(
    sample_type_id: int | None = Query(None),
    time_entry_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SampleBatch).order_by(SampleBatch.date_collected.desc())
    if sample_type_id is not None:
        stmt = stmt.where(SampleBatch.sample_type_id == sample_type_id)
    if time_entry_id is not None:
        stmt = stmt.where(SampleBatch.time_entry_id == time_entry_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{batch_id}", response_model=SampleBatchRead)
async def get_batch(batch_id: int, db: AsyncSession = Depends(get_db)):
    return await get_batch_or_404(batch_id, db)


@router.post("/", response_model=SampleBatchRead, status_code=status.HTTP_201_CREATED,
             dependencies=_edit)
async def create_batch(body: SampleBatchCreate, db: AsyncSession = Depends(get_db)):
    sample_type = await get_sample_type_or_404(body.sample_type_id, db)

    # Validate batch_num uniqueness
    existing = await db.execute(
        select(SampleBatch).where(SampleBatch.batch_num == body.batch_num)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Batch number already exists")

    # Validate time entry exists (independent of role check, which returns early
    # when no required roles are defined and would otherwise skip this check)
    if not await db.get(TimeEntry, body.time_entry_id):
        raise HTTPException(status_code=404, detail="Time entry not found")

    # Validate optional FK fields belong to the sample type
    if body.sample_subtype_id is not None:
        await validate_subtype_for_batch(body.sample_type_id, body.sample_subtype_id, db)
    if body.turnaround_option_id is not None:
        await validate_turnaround_for_batch(body.sample_type_id, body.turnaround_option_id, db)

    # Validate unit types all belong to the sample type
    unit_type_ids = [u.sample_unit_type_id for u in body.units]
    await validate_unit_types_for_batch(body.sample_type_id, unit_type_ids, db)

    # Validate employee's role matches sample type requirements
    await validate_employee_role_for_sample_type(body.time_entry_id, body.sample_type_id, db)

    # Validate inspector count
    await validate_inspector_count(sample_type, len(body.inspector_ids))

    # Validate all inspectors exist
    for emp_id in body.inspector_ids:
        emp = await db.get(Employee, emp_id)
        if not emp:
            raise HTTPException(status_code=404, detail=f"Employee {emp_id} not found")

    # Create batch
    batch = SampleBatch(
        sample_type_id=body.sample_type_id,
        sample_subtype_id=body.sample_subtype_id,
        turnaround_option_id=body.turnaround_option_id,
        time_entry_id=body.time_entry_id,
        batch_num=body.batch_num,
        is_report=body.is_report,
        date_collected=body.date_collected,
        notes=body.notes,
    )
    db.add(batch)
    await db.flush()  # get batch.id before creating child rows

    for unit in body.units:
        db.add(SampleBatchUnit(
            batch_id=batch.id,
            sample_unit_type_id=unit.sample_unit_type_id,
            quantity=unit.quantity,
        ))

    for emp_id in body.inspector_ids:
        db.add(SampleBatchInspector(batch_id=batch.id, employee_id=emp_id))

    await db.commit()
    await db.refresh(batch)
    return batch


@router.patch("/{batch_id}", response_model=SampleBatchRead, dependencies=_edit)
async def update_batch(
    batch_id: int, body: SampleBatchUpdate, db: AsyncSession = Depends(get_db)
):
    batch = await get_batch_or_404(batch_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(batch, field, value)
    await db.commit()
    await db.refresh(batch)
    return batch


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_edit)
async def delete_batch(batch_id: int, db: AsyncSession = Depends(get_db)):
    batch = await get_batch_or_404(batch_id, db)
    await db.delete(batch)
    await db.commit()
