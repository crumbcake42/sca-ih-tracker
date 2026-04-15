from sqlalchemy import or_, select, union, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import NoteEntityType
from app.contractors.models import Contractor
from app.deliverables.models import ProjectBuildingDeliverable, ProjectDeliverable
from app.lab_results.models import SampleBatch
from app.notes.models import Note
from app.notes.schemas import BlockingIssue
from app.projects.models import Project, ProjectContractorLink
from app.time_entries.models import TimeEntry


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
                # Set all old links to False
                await db.execute(
                    update(ProjectContractorLink)
                    .where(ProjectContractorLink.project_id == project.id)
                    .values(is_current=False)
                )
                # Create the new "Active" link
                new_link = ProjectContractorLink(
                    project_id=project.id, contractor_id=contractor.id, is_current=True
                )
                db.add(new_link)


_ENTITY_LINK_TEMPLATES = {
    NoteEntityType.PROJECT: "/projects/{}",
    NoteEntityType.TIME_ENTRY: "/time-entries/{}",
    NoteEntityType.DELIVERABLE: "/deliverables/{}",
    NoteEntityType.SAMPLE_BATCH: "/lab-results/batches/{}",
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
