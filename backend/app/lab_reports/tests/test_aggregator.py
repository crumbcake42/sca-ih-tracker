"""
Aggregator integration tests for Silo 4.

Verifies that unfulfilled, undismissed LabReportRequirement rows surface through
get_unfulfilled_requirements_for_project, and that saved or dismissed rows do not.
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.requirements import get_unfulfilled_requirements_for_project
from app.lab_reports.models import LabReportRequirement
from tests.seeds import (
    seed_employee,
    seed_employee_role,
    seed_project,
    seed_sample_batch,
    seed_sample_type,
    seed_school,
    seed_time_entry,
)


async def _seed_context(db: AsyncSession):
    school = await seed_school(db)
    project = await seed_project(db, school)
    emp = await seed_employee(db)
    role = await seed_employee_role(db, emp)
    entry = await seed_time_entry(db, emp, role, project, school)
    sample_type = await seed_sample_type(db)
    return project, entry, sample_type


class TestAggregatorSilo4:
    async def test_unfulfilled_row_surfaces(self, db_session: AsyncSession):
        project, entry, sample_type = await _seed_context(db_session)
        batch = await seed_sample_batch(db_session, entry, sample_type)
        db_session.add(
            LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        lab_reqs = [r for r in results if r.requirement_type == "lab_report"]
        assert len(lab_reqs) == 1
        assert lab_reqs[0].project_id == project.id

    async def test_saved_row_does_not_surface(self, db_session: AsyncSession):
        project, entry, sample_type = await _seed_context(db_session)
        batch = await seed_sample_batch(db_session, entry, sample_type, batch_num="AGG-S001")
        db_session.add(
            LabReportRequirement(
                project_id=project.id, sample_batch_id=batch.id, is_saved=True
            )
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        lab_reqs = [r for r in results if r.requirement_type == "lab_report"]
        assert lab_reqs == []

    async def test_dismissed_row_does_not_surface(self, db_session: AsyncSession):
        project, entry, sample_type = await _seed_context(db_session)
        batch = await seed_sample_batch(db_session, entry, sample_type, batch_num="AGG-D001")
        db_session.add(
            LabReportRequirement(
                project_id=project.id,
                sample_batch_id=batch.id,
                dismissed_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        lab_reqs = [r for r in results if r.requirement_type == "lab_report"]
        assert lab_reqs == []

    async def test_unfulfilled_requirement_has_correct_shape(self, db_session: AsyncSession):
        project, entry, sample_type = await _seed_context(db_session)
        batch = await seed_sample_batch(
            db_session, entry, sample_type, batch_num="AGG-SHAPE-001"
        )
        db_session.add(
            LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        lab_reqs = [r for r in results if r.requirement_type == "lab_report"]
        assert len(lab_reqs) == 1
        req = lab_reqs[0]
        assert req.requirement_type == "lab_report"
        assert req.is_dismissable is True
        assert req.is_dismissed is False
        assert req.label == "AGG-SHAPE-001"
