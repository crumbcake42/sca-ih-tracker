from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import func, or_, select, union, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import (
    NoteEntityType,
    NoteType,
    ProjectStatus,
    RequirementEvent,
    RFAStatus,
    SampleBatchStatus,
    SCADeliverableStatus,
    TimeEntryStatus,
    WACodeLevel,
    WACodeStatus,
)
from app.contractors.models import Contractor
from app.deliverables.models import (
    Deliverable,
    DeliverableWACodeTrigger,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.lab_results.models import SampleBatch, SampleTypeWACode
from app.notes.models import Note
from app.notes.schemas import BlockingIssue
from app.notes.service import auto_resolve_system_notes, create_system_note
from app.projects.models import Project, ProjectContractorLink
from app.time_entries.models import TimeEntry
from app.wa_codes.models import WACode
from app.work_auths.models import RFA, WorkAuth, WorkAuthBuildingCode, WorkAuthProjectCode

if TYPE_CHECKING:
    from app.projects.schemas import ProjectStatusRead

async def process_project_import(db: AsyncSession, project_data: dict):
    # 1. Handle the Project itself (Create or Update)
    project = (
        await db.execute(
            select(Project).where(
                Project.project_number == project_data["project_number"]
            )
        )
    ).scalar_one_or_none()

    if not project:
        project = Project(**project_data)
        db.add(project)
        await db.flush()  # Get the ID without committing yet

    # 2. Handle the Contractor Link
    new_contractor_name = project_data.get("contractor_name")
    if new_contractor_name:
        contractor = (
            await db.execute(
                select(Contractor).where(Contractor.name == new_contractor_name)
            )
        ).scalar_one_or_none()

        if contractor:
            # Look for the CURRENT active link
            current_link = (
                await db.execute(
                    select(ProjectContractorLink)
                    .where(ProjectContractorLink.project_id == project.id)
                    .where(ProjectContractorLink.is_current)
                )
            ).scalar_one_or_none()

            # If no link exists, or the contractor has changed:
            if not current_link or current_link.contractor_id != contractor.id:
                prior_contractor_id = (
                    current_link.contractor_id if current_link else None
                )
                # Set all old links to False
                await db.execute(
                    update(ProjectContractorLink)
                    .where(ProjectContractorLink.project_id == project.id)
                    .values(is_current=False)
                )
                await db.flush()
                # Fire unlink event for the displaced contractor (if any)
                if prior_contractor_id is not None:
                    from app.common.requirements.dispatcher import dispatch_requirement_event

                    await dispatch_requirement_event(
                        project_id=project.id,
                        event=RequirementEvent.CONTRACTOR_UNLINKED,
                        payload={"contractor_id": prior_contractor_id},
                        db=db,
                    )
                # Create the new "Active" link
                new_link = ProjectContractorLink(
                    project_id=project.id, contractor_id=contractor.id, is_current=True
                )
                db.add(new_link)
                await db.flush()
                from app.common.requirements.dispatcher import dispatch_requirement_event

                await dispatch_requirement_event(
                    project_id=project.id,
                    event=RequirementEvent.CONTRACTOR_LINKED,
                    payload={"contractor_id": contractor.id},
                    db=db,
                )


_DERIVABLE_SCA_STATUSES = {
    SCADeliverableStatus.PENDING_WA,
    SCADeliverableStatus.PENDING_RFA,
    SCADeliverableStatus.OUTSTANDING,
}

_ACTIVE_CODE_STATUSES = {WACodeStatus.ACTIVE, WACodeStatus.ADDED_BY_RFA}


def _compute_sca_status(
    trigger_ids: set[int], codes: dict[int, WACodeStatus]
) -> SCADeliverableStatus:
    """
    Derive SCA deliverable status from trigger WA code IDs and the current
    status of those codes on the WA. `codes` maps wa_code_id → status for
    all non-removed codes relevant to the deliverable's level and scope.
    """
    relevant = {
        code_id: status
        for code_id, status in codes.items()
        if code_id in trigger_ids and status != WACodeStatus.REMOVED
    }
    if not relevant:
        return SCADeliverableStatus.PENDING_WA
    if any(s in _ACTIVE_CODE_STATUSES for s in relevant.values()):
        return SCADeliverableStatus.OUTSTANDING
    return SCADeliverableStatus.PENDING_RFA


async def recalculate_deliverable_sca_status(project_id: int, db: AsyncSession) -> None:
    """
    Recompute `sca_status` for every derivable project_deliverable and
    project_building_deliverable row on this project.

    Derivable statuses: PENDING_WA, PENDING_RFA, OUTSTANDING.
    Manual terminal statuses (UNDER_REVIEW, REJECTED, APPROVED) are never
    overwritten.
    """
    wa = (
        await db.execute(select(WorkAuth).where(WorkAuth.project_id == project_id))
    ).scalar_one_or_none()

    if wa is None:
        # No WA at all — everything reverts to pending_wa.
        for model in (ProjectDeliverable, ProjectBuildingDeliverable):
            await db.execute(
                update(model)
                .where(model.project_id == project_id)
                .where(model.sca_status.in_(_DERIVABLE_SCA_STATUSES))
                .values(sca_status=SCADeliverableStatus.PENDING_WA)
                .execution_options(synchronize_session=False)
            )
        return

    # Load project-level WA codes: {wa_code_id: status}
    proj_code_rows = (
        await db.execute(
            select(WorkAuthProjectCode.wa_code_id, WorkAuthProjectCode.status).where(
                WorkAuthProjectCode.work_auth_id == wa.id
            )
        )
    ).all()
    proj_codes: dict[int, WACodeStatus] = {r.wa_code_id: r.status for r in proj_code_rows}

    # Load building-level WA codes: {(wa_code_id, school_id): status}
    bldg_code_rows = (
        await db.execute(
            select(
                WorkAuthBuildingCode.wa_code_id,
                WorkAuthBuildingCode.school_id,
                WorkAuthBuildingCode.status,
            ).where(
                WorkAuthBuildingCode.work_auth_id == wa.id,
                WorkAuthBuildingCode.project_id == project_id,
            )
        )
    ).all()
    bldg_codes: dict[tuple[int, int], WACodeStatus] = {
        (r.wa_code_id, r.school_id): r.status for r in bldg_code_rows
    }

    # Load all trigger mappings: {deliverable_id: {wa_code_id, ...}}
    trigger_rows = (
        await db.execute(
            select(
                DeliverableWACodeTrigger.deliverable_id,
                DeliverableWACodeTrigger.wa_code_id,
            )
        )
    ).all()
    triggers: dict[int, set[int]] = {}
    for r in trigger_rows:
        triggers.setdefault(r.deliverable_id, set()).add(r.wa_code_id)

    # Update project-level deliverables.
    pd_rows = (
        await db.execute(
            select(ProjectDeliverable)
            .where(ProjectDeliverable.project_id == project_id)
            .where(ProjectDeliverable.sca_status.in_(_DERIVABLE_SCA_STATUSES))
        )
    ).scalars().all()

    for pd in pd_rows:
        new_status = _compute_sca_status(triggers.get(pd.deliverable_id, set()), proj_codes)
        if pd.sca_status != new_status:
            pd.sca_status = new_status

    # Update building-level deliverables.
    pbd_rows = (
        await db.execute(
            select(ProjectBuildingDeliverable)
            .where(ProjectBuildingDeliverable.project_id == project_id)
            .where(ProjectBuildingDeliverable.sca_status.in_(_DERIVABLE_SCA_STATUSES))
        )
    ).scalars().all()

    for pbd in pbd_rows:
        codes_for_school: dict[int, WACodeStatus] = {
            code_id: status
            for (code_id, school_id), status in bldg_codes.items()
            if school_id == pbd.school_id
        }
        new_status = _compute_sca_status(
            triggers.get(pbd.deliverable_id, set()), codes_for_school
        )
        if pbd.sca_status != new_status:
            pbd.sca_status = new_status

    await db.flush()


async def ensure_deliverables_exist(project_id: int, db: AsyncSession) -> None:
    """
    Create any missing project_deliverable / project_building_deliverable rows
    implied by the WA codes currently on the project.

    Idempotent: rows that already exist are never re-created.
    Respects Deliverable.level: PROJECT deliverables are triggered by
    project-level WA codes; BUILDING deliverables by building-level codes
    (one row per linked school).
    """
    wa = (
        await db.execute(select(WorkAuth).where(WorkAuth.project_id == project_id))
    ).scalar_one_or_none()

    if wa is None:
        return

    # Project-level code IDs on this WA.
    proj_code_ids: set[int] = set(
        (
            await db.execute(
                select(WorkAuthProjectCode.wa_code_id).where(
                    WorkAuthProjectCode.work_auth_id == wa.id
                )
            )
        ).scalars().all()
    )

    # Building-level codes: {school_id: {wa_code_id, ...}}
    bldg_rows = (
        await db.execute(
            select(WorkAuthBuildingCode.wa_code_id, WorkAuthBuildingCode.school_id).where(
                WorkAuthBuildingCode.work_auth_id == wa.id,
                WorkAuthBuildingCode.project_id == project_id,
            )
        )
    ).all()
    bldg_codes_by_school: dict[int, set[int]] = {}
    for r in bldg_rows:
        bldg_codes_by_school.setdefault(r.school_id, set()).add(r.wa_code_id)

    all_code_ids = proj_code_ids | {r.wa_code_id for r in bldg_rows}
    if not all_code_ids:
        return

    # Deliverables triggered by any of those codes, with their level.
    trigger_rows = (
        await db.execute(
            select(
                DeliverableWACodeTrigger.deliverable_id,
                DeliverableWACodeTrigger.wa_code_id,
                Deliverable.level,
            )
            .join(Deliverable, DeliverableWACodeTrigger.deliverable_id == Deliverable.id)
            .where(DeliverableWACodeTrigger.wa_code_id.in_(all_code_ids))
        )
    ).all()

    if not trigger_rows:
        return

    # {deliverable_id: (level, {wa_code_id, ...})}
    deliv_info: dict[int, tuple[WACodeLevel, set[int]]] = {}
    for r in trigger_rows:
        if r.deliverable_id not in deliv_info:
            deliv_info[r.deliverable_id] = (r.level, set())
        deliv_info[r.deliverable_id][1].add(r.wa_code_id)

    # Existing rows (avoid duplicate inserts).
    existing_pd: set[int] = set(
        (
            await db.execute(
                select(ProjectDeliverable.deliverable_id).where(
                    ProjectDeliverable.project_id == project_id
                )
            )
        ).scalars().all()
    )
    existing_pbd: set[tuple[int, int]] = set(
        (
            await db.execute(
                select(
                    ProjectBuildingDeliverable.deliverable_id,
                    ProjectBuildingDeliverable.school_id,
                ).where(ProjectBuildingDeliverable.project_id == project_id)
            )
        ).scalars().all()
    )

    for deliv_id, (level, code_ids) in deliv_info.items():
        if level == WACodeLevel.PROJECT:
            if code_ids & proj_code_ids and deliv_id not in existing_pd:
                db.add(
                    ProjectDeliverable(
                        project_id=project_id,
                        deliverable_id=deliv_id,
                        created_by_id=SYSTEM_USER_ID,
                        updated_by_id=SYSTEM_USER_ID,
                    )
                )
        else:
            for school_id, school_code_ids in bldg_codes_by_school.items():
                if code_ids & school_code_ids and (deliv_id, school_id) not in existing_pbd:
                    db.add(
                        ProjectBuildingDeliverable(
                            project_id=project_id,
                            deliverable_id=deliv_id,
                            school_id=school_id,
                            created_by_id=SYSTEM_USER_ID,
                            updated_by_id=SYSTEM_USER_ID,
                        )
                    )

    await db.flush()


async def check_sample_type_gap_note(project_id: int, db: AsyncSession) -> None:
    """
    Emit a blocking system note if any sample type used on this project requires a
    WA code not present on the project's work auth. Auto-resolves if all gaps are filled.
    """
    wa = (
        await db.execute(select(WorkAuth).where(WorkAuth.project_id == project_id))
    ).scalar_one_or_none()
    if wa is None:
        return

    proj_code_ids: set[int] = set(
        (
            await db.execute(
                select(WorkAuthProjectCode.wa_code_id).where(
                    WorkAuthProjectCode.work_auth_id == wa.id
                )
            )
        ).scalars().all()
    )
    bldg_code_ids: set[int] = set(
        (
            await db.execute(
                select(WorkAuthBuildingCode.wa_code_id).where(
                    WorkAuthBuildingCode.work_auth_id == wa.id,
                    WorkAuthBuildingCode.project_id == project_id,
                )
            )
        ).scalars().all()
    )
    wa_code_ids = proj_code_ids | bldg_code_ids

    sample_type_ids: set[int] = set(
        (
            await db.execute(
                select(SampleBatch.sample_type_id)
                .join(TimeEntry, SampleBatch.time_entry_id == TimeEntry.id)
                .where(TimeEntry.project_id == project_id)
                .distinct()
            )
        ).scalars().all()
    )

    if not sample_type_ids:
        await auto_resolve_system_notes(
            NoteEntityType.PROJECT, project_id, NoteType.MISSING_SAMPLE_TYPE_WA_CODE, db
        )
        return

    required_code_ids: set[int] = set(
        (
            await db.execute(
                select(SampleTypeWACode.wa_code_id).where(
                    SampleTypeWACode.sample_type_id.in_(sample_type_ids)
                )
            )
        ).scalars().all()
    )

    missing = required_code_ids - wa_code_ids
    if missing:
        codes = (
            await db.execute(select(WACode.code).where(WACode.id.in_(missing)))
        ).scalars().all()
        body = (
            "Sample type requires WA code(s) not on this project's work auth: "
            + ", ".join(sorted(codes))
        )
        await create_system_note(
            NoteEntityType.PROJECT, project_id, NoteType.MISSING_SAMPLE_TYPE_WA_CODE, body, db
        )
    else:
        await auto_resolve_system_notes(
            NoteEntityType.PROJECT, project_id, NoteType.MISSING_SAMPLE_TYPE_WA_CODE, db
        )


async def derive_project_status(
    project_id: int,
    db: AsyncSession,
) -> "ProjectStatusRead":
    from app.projects.schemas import ProjectStatusRead

    project = await db.get(Project, project_id)
    if project and project.is_locked:
        return ProjectStatusRead(
            project_id=project_id,
            status=ProjectStatus.LOCKED,
            has_work_auth=False,
            pending_rfa_count=0,
            outstanding_deliverable_count=0,
            unconfirmed_time_entry_count=0,
            blocking_issues=[],
        )

    blocking_issues = await get_blocking_notes_for_project(project_id, db)

    wa = (
        await db.execute(select(WorkAuth).where(WorkAuth.project_id == project_id))
    ).scalar_one_or_none()

    has_work_auth = wa is not None

    pending_rfa_count: int = 0
    if wa is not None:
        pending_rfa_count = (
            await db.execute(
                select(func.count())
                .select_from(RFA)
                .where(RFA.work_auth_id == wa.id, RFA.status == RFAStatus.PENDING)
            )
        ).scalar_one()

    pd_count: int = (
        await db.execute(
            select(func.count())
            .select_from(ProjectDeliverable)
            .where(
                ProjectDeliverable.project_id == project_id,
                ProjectDeliverable.sca_status.in_(_DERIVABLE_SCA_STATUSES),
            )
        )
    ).scalar_one()
    pbd_count: int = (
        await db.execute(
            select(func.count())
            .select_from(ProjectBuildingDeliverable)
            .where(
                ProjectBuildingDeliverable.project_id == project_id,
                ProjectBuildingDeliverable.sca_status.in_(_DERIVABLE_SCA_STATUSES),
            )
        )
    ).scalar_one()
    outstanding_deliverable_count = pd_count + pbd_count

    time_entry_count: int = (
        await db.execute(
            select(func.count())
            .select_from(TimeEntry)
            .where(TimeEntry.project_id == project_id)
        )
    ).scalar_one()

    unconfirmed_time_entry_count: int = (
        await db.execute(
            select(func.count())
            .select_from(TimeEntry)
            .where(
                TimeEntry.project_id == project_id,
                TimeEntry.status == TimeEntryStatus.ASSUMED,
            )
        )
    ).scalar_one()

    if blocking_issues:
        status = ProjectStatus.BLOCKED
    elif time_entry_count == 0:
        status = ProjectStatus.SETUP
    elif (
        outstanding_deliverable_count == 0
        and pending_rfa_count == 0
        and unconfirmed_time_entry_count == 0
    ):
        status = ProjectStatus.READY_TO_CLOSE
    else:
        status = ProjectStatus.IN_PROGRESS

    return ProjectStatusRead(
        project_id=project_id,
        status=status,
        has_work_auth=has_work_auth,
        pending_rfa_count=pending_rfa_count,
        outstanding_deliverable_count=outstanding_deliverable_count,
        unconfirmed_time_entry_count=unconfirmed_time_entry_count,
        blocking_issues=blocking_issues,
    )


async def lock_project_records(project_id: int, db: AsyncSession, user_id: int) -> None:
    """
    Close a project: cascade LOCKED status to all time entries and active batches.
    Raises 409 if any unresolved blocking notes exist on the project.
    """
    blocking_issues = await get_blocking_notes_for_project(project_id, db)
    if blocking_issues:
        raise HTTPException(
            status_code=409,
            detail={"blocking_issues": [bi.model_dump() for bi in blocking_issues]},
        )

    await db.execute(
        update(TimeEntry)
        .where(
            TimeEntry.project_id == project_id,
            TimeEntry.status.in_([TimeEntryStatus.ASSUMED, TimeEntryStatus.ENTERED]),
        )
        .values(status=TimeEntryStatus.LOCKED, updated_by_id=user_id)
        .execution_options(synchronize_session=False)
    )

    te_ids_sq = (
        select(TimeEntry.id).where(TimeEntry.project_id == project_id).scalar_subquery()
    )
    await db.execute(
        update(SampleBatch)
        .where(
            SampleBatch.time_entry_id.in_(te_ids_sq),
            SampleBatch.status == SampleBatchStatus.ACTIVE,
        )
        .values(status=SampleBatchStatus.LOCKED, updated_by_id=user_id)
        .execution_options(synchronize_session=False)
    )

    project = await db.get(Project, project_id)
    project.is_locked = True
    project.updated_by_id = user_id
    await db.flush()


_ENTITY_LINK_TEMPLATES = {
    NoteEntityType.PROJECT: "/projects/{}",
    NoteEntityType.TIME_ENTRY: "/time-entries/{}",
    NoteEntityType.DELIVERABLE: "/deliverables/{}",
    NoteEntityType.SAMPLE_BATCH: "/lab-results/batches/{}",
    NoteEntityType.CONTRACTOR_PAYMENT_RECORD: "/contractor-payment-records/{}",
}


async def get_blocking_notes_for_project(
    project_id: int,
    db: AsyncSession,
) -> list[BlockingIssue]:
    """
    Aggregate all unresolved blocking notes across every entity that belongs
    to this project: the project itself, its time entries, its deliverables
    (project-level and building-level), and its sample batches.

    Note on deliverables: `project_deliverables` and
    `project_building_deliverables` have no surrogate ID; notes on deliverables
    use the `deliverable_id` (template ID) as `entity_id`. A note on deliverable
    template #5 will appear here for any project that has that deliverable.

    Note on batches: only batches linked to a time entry (non-null
    `time_entry_id`) are reachable from the project. Batches with no time entry
    have no project association and are excluded.

    Returns list ordered by created_at ascending.
    """
    te_ids_sq = (
        select(TimeEntry.id)
        .where(TimeEntry.project_id == project_id)
        .scalar_subquery()
    )

    pd_ids = select(ProjectDeliverable.deliverable_id).where(
        ProjectDeliverable.project_id == project_id
    )
    pbd_ids = select(ProjectBuildingDeliverable.deliverable_id).where(
        ProjectBuildingDeliverable.project_id == project_id
    )
    deliverable_ids_sq = union(pd_ids, pbd_ids).subquery()

    sb_ids_sq = (
        select(SampleBatch.id)
        .join(TimeEntry, SampleBatch.time_entry_id == TimeEntry.id)
        .where(TimeEntry.project_id == project_id)
        .scalar_subquery()
    )

    rows = (
        await db.execute(
            select(Note)
            .where(
                Note.is_blocking.is_(True),
                Note.is_resolved.is_(False),
                Note.parent_note_id.is_(None),  # replies are never blocking
                or_(
                    (Note.entity_type == NoteEntityType.PROJECT)
                    & (Note.entity_id == project_id),
                    (Note.entity_type == NoteEntityType.TIME_ENTRY)
                    & Note.entity_id.in_(te_ids_sq),
                    (Note.entity_type == NoteEntityType.DELIVERABLE)
                    & Note.entity_id.in_(
                        select(deliverable_ids_sq.c.deliverable_id)
                    ),
                    (Note.entity_type == NoteEntityType.SAMPLE_BATCH)
                    & Note.entity_id.in_(sb_ids_sq),
                ),
            )
            .order_by(Note.created_at)
        )
    ).scalars().all()

    return [
        BlockingIssue(
            note_id=n.id,
            entity_type=n.entity_type,
            entity_id=n.entity_id,
            body=n.body,
            entity_label=f"{n.entity_type.value.replace('_', ' ').title()} #{n.entity_id}",
            link=_ENTITY_LINK_TEMPLATES[n.entity_type].format(n.entity_id),
        )
        for n in rows
    ]
