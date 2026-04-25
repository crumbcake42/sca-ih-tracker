from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.factories import create_guarded_delete_router, create_readonly_router
from app.contractors.models import Contractor as ContractorModel
from app.contractors.schemas import Contractor, ContractorCreate, ContractorUpdate
from app.database import get_db
from app.projects.models.links import ProjectContractorLink
from app.users.dependencies import get_current_user
from app.users.models import User

router = APIRouter()

router.include_router(
    create_readonly_router(
        model=ContractorModel,
        read_schema=Contractor,
        default_sort=ContractorModel.name.asc(),
        search_attr=ContractorModel.name,
    )
)


@router.get("/{contractor_id}", response_model=Contractor)
async def get_contractor(contractor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ContractorModel).where(ContractorModel.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    return contractor


@router.post("/", response_model=Contractor, status_code=201)
async def create_contractor(
    data: ContractorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_contractor = ContractorModel(**data.model_dump(), created_by_id=current_user.id)
    db.add(new_contractor)
    await db.commit()
    await db.refresh(new_contractor)
    return new_contractor


router.include_router(
    create_guarded_delete_router(
        model=ContractorModel,
        not_found_detail="Contractor not found",
        refs=[(ProjectContractorLink, ProjectContractorLink.contractor_id, "project_contractors_links")],
        path_param_name="contractor_id",
    )
)


@router.patch("/{contractor_id}", response_model=Contractor)
async def update_contractor(
    contractor_id: int,
    data: ContractorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ContractorModel).where(ContractorModel.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contractor, field, value)
    contractor.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(contractor)
    return contractor
