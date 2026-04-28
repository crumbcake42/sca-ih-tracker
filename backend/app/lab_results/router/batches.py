from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RequirementEvent, SampleBatchStatus
from app.common.requirements.dispatcher import dispatch_requirement_event
from app.database import get_db
from app.employees.models import Employee
from app.lab_results.models import (
    SampleBatch,
    SampleBatchInspector,
    SampleBatchUnit,
)
from app.lab_results.schemas import (
    QuickAddBatchCreate,
    SampleBatchCreate,
    SampleBatchRead,
    SampleBatchUpdate,
)
from app.lab_results.service import (
    get_batch_or_404,
    get_sample_type_or_404,
    quick_add_batch,
    validate_employee_role_for_sample_type,
    validate_inspector_count,
    validate_subtype_for_batch,
    validate_turnaround_for_batch,
    validate_unit_types_for_batch,
)
from app.projects.services import (
    check_sample_type_gap_note,
    ensure_deliverables_exist,
    recalculate_deliverable_sca_status,
)
from app.time_entries.models import TimeEntry
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter(prefix="/batches", tags=["Lab Results — Batches"])

_edit_dep = PermissionChecker(PermissionName.PROJECT_EDIT)


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


@router.post("/", response_model=SampleBatchRead, status_code=status.HTTP_201_CREATED)
async def create_batch(
    body: SampleBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit_dep),
):
    sample_type = await get_sample_type_or_404(body.sample_type_id, db)

    # Validate batch_num uniqueness
    existing = await db.execute(
        select(SampleBatch).where(SampleBatch.batch_num == body.batch_num)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Batch number already exists")

    # Validate time entry exists when one is provided
    time_entry: TimeEntry | None = None
    if body.time_entry_id is not None:
        time_entry = await db.get(TimeEntry, body.time_entry_id)
        if not time_entry:
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
        date_collected=body.date_collected,
        notes=body.notes,
        created_by_id=current_user.id,
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

    if time_entry is not None:
        await ensure_deliverables_exist(time_entry.project_id, db)
        await recalculate_deliverable_sca_status(time_entry.project_id, db)
        await check_sample_type_gap_note(time_entry.project_id, db)
        await dispatch_requirement_event(
            project_id=time_entry.project_id,
            event=RequirementEvent.BATCH_CREATED,
            payload={"batch_id": batch.id},
            db=db,
        )
    await db.commit()
    await db.refresh(batch)
    return batch


@router.patch("/{batch_id}", response_model=SampleBatchRead)
async def update_batch(
    batch_id: int,
    body: SampleBatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit_dep),
):
    batch = await get_batch_or_404(batch_id, db)
    if batch.status == SampleBatchStatus.LOCKED:
        raise HTTPException(status_code=422, detail="Cannot modify a locked batch")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(batch, field, value)
    batch.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(batch)
    return batch


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(_edit_dep)])
async def delete_batch(batch_id: int, db: AsyncSession = Depends(get_db)):
    batch = await get_batch_or_404(batch_id, db)
    if batch.status == SampleBatchStatus.LOCKED:
        raise HTTPException(status_code=422, detail="Cannot delete a locked batch")
    await db.delete(batch)
    await db.commit()


@router.post("/{batch_id}/discard", response_model=SampleBatchRead)
async def discard_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit_dep),
):
    batch = await get_batch_or_404(batch_id, db)
    if batch.status == SampleBatchStatus.LOCKED:
        raise HTTPException(status_code=422, detail="Cannot discard a locked batch")
    if batch.status == SampleBatchStatus.DISCARDED:
        raise HTTPException(status_code=422, detail="Batch is already discarded")
    batch.status = SampleBatchStatus.DISCARDED
    batch.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(batch)
    return batch


@router.post("/quick-add", response_model=SampleBatchRead, status_code=status.HTTP_201_CREATED)
async def quick_add(
    body: QuickAddBatchCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_edit_dep),
):
    batch = await quick_add_batch(body, db)
    await ensure_deliverables_exist(body.project_id, db)
    await recalculate_deliverable_sca_status(body.project_id, db)
    await check_sample_type_gap_note(body.project_id, db)
    await db.commit()
    return batch
