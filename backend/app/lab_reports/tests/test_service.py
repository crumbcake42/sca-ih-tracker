"""
Service tests for lab_reports: LabReportHandler classmethods.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RequirementEvent
from app.lab_reports.models import LabReportRequirement
from app.lab_reports.service import LabReportHandler
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
    batch = await seed_sample_batch(db, entry, sample_type)
    return project, batch


class TestHandleEventBatchCreated:
    async def test_creates_requirement_on_batch_created(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)

        await LabReportHandler.handle_event(
            project.id, RequirementEvent.BATCH_CREATED, {"batch_id": batch.id}, db_session
        )
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(LabReportRequirement).where(
                    LabReportRequirement.sample_batch_id == batch.id
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].project_id == project.id
        assert rows[0].is_saved is False

    async def test_idempotent_no_duplicate_on_second_dispatch(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)

        await LabReportHandler.handle_event(
            project.id, RequirementEvent.BATCH_CREATED, {"batch_id": batch.id}, db_session
        )
        await db_session.flush()
        await LabReportHandler.handle_event(
            project.id, RequirementEvent.BATCH_CREATED, {"batch_id": batch.id}, db_session
        )
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(LabReportRequirement).where(
                    LabReportRequirement.sample_batch_id == batch.id,
                    LabReportRequirement.dismissed_at.is_(None),
                )
            )
        ).scalars().all()
        assert len(rows) == 1

    async def test_dismissed_row_does_not_block_rematerialization(self, db_session: AsyncSession):
        from datetime import datetime

        project, batch = await _seed_context(db_session)

        dismissed = LabReportRequirement(
            project_id=project.id,
            sample_batch_id=batch.id,
            dismissed_at=datetime(2025, 12, 1),
        )
        db_session.add(dismissed)
        await db_session.flush()

        await LabReportHandler.handle_event(
            project.id, RequirementEvent.BATCH_CREATED, {"batch_id": batch.id}, db_session
        )
        await db_session.flush()

        active_rows = (
            await db_session.execute(
                select(LabReportRequirement).where(
                    LabReportRequirement.sample_batch_id == batch.id,
                    LabReportRequirement.dismissed_at.is_(None),
                )
            )
        ).scalars().all()
        assert len(active_rows) == 1
        assert active_rows[0].id != dismissed.id

    async def test_unrecognized_event_is_noop(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)

        await LabReportHandler.handle_event(
            project.id, RequirementEvent.TIME_ENTRY_CREATED, {"batch_id": batch.id}, db_session
        )
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(LabReportRequirement).where(
                    LabReportRequirement.sample_batch_id == batch.id
                )
            )
        ).scalars().all()
        assert rows == []


class TestGetUnfulfilledForProject:
    async def test_returns_unsaved_undismissed_rows(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)
        db_session.add(
            LabReportRequirement(
                project_id=project.id, sample_batch_id=batch.id, is_saved=False
            )
        )
        await db_session.flush()

        result = await LabReportHandler.get_unfulfilled_for_project(project.id, db_session)
        assert len(result) == 1

    async def test_excludes_saved_rows(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)
        db_session.add(
            LabReportRequirement(
                project_id=project.id, sample_batch_id=batch.id, is_saved=True
            )
        )
        await db_session.flush()

        result = await LabReportHandler.get_unfulfilled_for_project(project.id, db_session)
        assert result == []

    async def test_excludes_dismissed_rows(self, db_session: AsyncSession):
        from datetime import datetime

        project, batch = await _seed_context(db_session)
        db_session.add(
            LabReportRequirement(
                project_id=project.id,
                sample_batch_id=batch.id,
                dismissed_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        result = await LabReportHandler.get_unfulfilled_for_project(project.id, db_session)
        assert result == []


class TestValidateTemplateParams:
    def test_empty_dict_is_valid(self):
        LabReportHandler.validate_template_params({})

    def test_non_empty_dict_raises(self):
        with pytest.raises(ValueError, match="not configurable via requirement-triggers"):
            LabReportHandler.validate_template_params({"key": "value"})
