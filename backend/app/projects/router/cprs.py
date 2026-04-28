from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contractors.models import Contractor
from app.cprs.models import ContractorPaymentRecord
from app.cprs.schemas import ContractorPaymentRecordCreate, ContractorPaymentRecordRead
from app.database import get_db
from app.projects.models import Project, ProjectContractorLink
from app.users.dependencies import PermissionChecker, PermissionName
from app.users.models import User

router = APIRouter(prefix="/{project_id}/cprs", tags=["CPRs"])


@router.get("/", response_model=list[ContractorPaymentRecordRead])
async def list_contractor_payment_records(
    project_id: int,
    include_dismissed: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(ContractorPaymentRecord).where(
        ContractorPaymentRecord.project_id == project_id
    )
    if not include_dismissed:
        stmt = stmt.where(ContractorPaymentRecord.dismissed_at.is_(None))

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ContractorPaymentRecordRead, status_code=status.HTTP_201_CREATED)
async def create_contractor_payment_record(
    project_id: int,
    body: ContractorPaymentRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Manually create a CPR row (administrative correction or missed event)."""
    if body.project_id != project_id:
        raise HTTPException(status_code=422, detail="project_id in body must match URL")
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    contractor = await db.get(Contractor, body.contractor_id)
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    link = (
        await db.execute(
            select(ProjectContractorLink).where(
                ProjectContractorLink.project_id == project_id,
                ProjectContractorLink.contractor_id == body.contractor_id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=422, detail="Contractor is not linked to this project")

    record = ContractorPaymentRecord(
        project_id=project_id,
        contractor_id=body.contractor_id,
        notes=body.notes,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
