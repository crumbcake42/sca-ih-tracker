from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.factories import create_guarded_delete_router, create_readonly_router
from app.database import get_db
from app.dep_filings.models import DEPFilingForm, ProjectDEPFiling
from app.dep_filings.schemas import (
    DEPFilingFormCreate,
    DEPFilingFormRead,
    DEPFilingFormUpdate,
    ProjectDEPFilingDismiss,
    ProjectDEPFilingRead,
    ProjectDEPFilingUpdate,
)
from app.users.dependencies import PermissionChecker, PermissionName, get_current_user
from app.users.models import User


# ---------------------------------------------------------------------------
# Form admin sub-router — all routes under /dep-filings/forms
# ---------------------------------------------------------------------------

_forms_router = APIRouter(prefix="/forms", tags=["DEP filing forms"])

_forms_router.include_router(
    create_readonly_router(
        DEPFilingForm,
        DEPFilingFormRead,
        default_sort=DEPFilingForm.display_order.asc(),
    )
)

_forms_router.include_router(
    create_guarded_delete_router(
        model=DEPFilingForm,
        not_found_detail="DEP filing form not found",
        refs=[(ProjectDEPFiling, ProjectDEPFiling.dep_filing_form_id, "project_dep_filings")],
        path_param_name="form_id",
    )
)


@_forms_router.get("/{form_id}", response_model=DEPFilingFormRead)
async def get_dep_filing_form(
    form_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    form = await db.get(DEPFilingForm, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="DEP filing form not found")
    return form


@_forms_router.post("/", response_model=DEPFilingFormRead, status_code=status.HTTP_201_CREATED)
async def create_dep_filing_form(
    body: DEPFilingFormCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    existing = (
        await db.execute(select(DEPFilingForm).where(DEPFilingForm.code == body.code))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=422, detail=f"code '{body.code}' already exists")

    form = DEPFilingForm(**body.model_dump(), created_by_id=current_user.id)
    db.add(form)
    await db.commit()
    await db.refresh(form)
    return form


@_forms_router.patch("/{form_id}", response_model=DEPFilingFormRead)
async def update_dep_filing_form(
    form_id: int,
    body: DEPFilingFormUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    form = await db.get(DEPFilingForm, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="DEP filing form not found")

    updates = body.model_dump(exclude_unset=True)
    if "code" in updates and updates["code"] != form.code:
        existing = (
            await db.execute(
                select(DEPFilingForm).where(DEPFilingForm.code == updates["code"])
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=422, detail=f"code '{updates['code']}' already exists")

    for field, value in updates.items():
        setattr(form, field, value)
    form.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(form)
    return form


# ---------------------------------------------------------------------------
# Item router — routes scoped to a single ProjectDEPFiling row
# Project-scoped list/create endpoints live in app/projects/router/dep_filings.py
# ---------------------------------------------------------------------------

dep_filing_router = APIRouter(prefix="/dep-filings", tags=["DEP filings"])
dep_filing_router.include_router(_forms_router)


@dep_filing_router.patch(
    "/{filing_id}",
    response_model=ProjectDEPFilingRead,
)
async def update_dep_filing(
    filing_id: int,
    body: ProjectDEPFilingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    filing = await db.get(ProjectDEPFiling, filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="DEP filing not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(filing, field, value)

    # Stamp saved_at when is_saved transitions to True
    if updates.get("is_saved") is True and filing.saved_at is None:
        filing.saved_at = datetime.now(UTC).replace(tzinfo=None)

    filing.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(filing)
    return filing


@dep_filing_router.post(
    "/{filing_id}/dismiss",
    response_model=ProjectDEPFilingRead,
)
async def dismiss_dep_filing(
    filing_id: int,
    body: ProjectDEPFilingDismiss,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    filing = await db.get(ProjectDEPFiling, filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="DEP filing not found")
    if filing.dismissed_at is not None:
        raise HTTPException(status_code=422, detail="DEP filing is already dismissed")
    if not filing.is_dismissable:
        raise HTTPException(status_code=422, detail="This requirement type cannot be dismissed")

    filing.dismissal_reason = body.dismissal_reason
    filing.dismissed_by_id = current_user.id
    filing.dismissed_at = datetime.now(UTC).replace(tzinfo=None)
    filing.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(filing)
    return filing


@dep_filing_router.delete(
    "/{filing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_dep_filing(
    filing_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(PermissionChecker(PermissionName.PROJECT_EDIT)),
):
    """Only pristine rows (unsaved, undismissed, no file attached) may be deleted.
    For progressed rows, use the dismiss endpoint instead."""
    filing = await db.get(ProjectDEPFiling, filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="DEP filing not found")
    if filing.is_saved or filing.dismissed_at is not None or filing.file_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Only pristine rows (unsaved, undismissed, no file) may be deleted. Use the dismiss endpoint instead.",
        )

    await db.delete(filing)
    await db.commit()
