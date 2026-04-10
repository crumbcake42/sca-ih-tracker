from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.contractors.models import Contractor
from app.projects.models import Project, ProjectContractorLink


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
