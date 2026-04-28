"""
ORM model tests for LabReportRequirement.

Verifies round-trip persistence, partial unique index behavior,
protocol property correctness, and AuditMixin/DismissibleMixin columns.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    batch = await seed_sample_batch(db, entry, sample_type)
    return project, batch


class TestLabReportRequirementModel:
    async def test_round_trip_insert(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)
        req = LabReportRequirement(
            project_id=project.id,
            sample_batch_id=batch.id,
            is_saved=False,
        )
        db_session.add(req)
        await db_session.flush()

        fetched = await db_session.get(LabReportRequirement, req.id)
        assert fetched is not None
        assert fetched.project_id == project.id
        assert fetched.sample_batch_id == batch.id
        assert fetched.is_saved is False
        assert fetched.dismissed_at is None

    async def test_audit_columns_populated(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)
        req = LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        db_session.add(req)
        await db_session.flush()

        fetched = await db_session.get(LabReportRequirement, req.id)
        assert fetched.created_at is not None
        assert fetched.updated_at is not None

    async def test_dismissible_columns_present(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)
        req = LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        db_session.add(req)
        await db_session.flush()

        fetched = await db_session.get(LabReportRequirement, req.id)
        assert fetched.dismissal_reason is None
        assert fetched.dismissed_by_id is None
        assert fetched.dismissed_at is None

    async def test_is_fulfilled_reflects_is_saved(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)
        req = LabReportRequirement(project_id=project.id, sample_batch_id=batch.id, is_saved=False)
        db_session.add(req)
        await db_session.flush()

        assert req.is_fulfilled is False
        req.is_saved = True
        assert req.is_fulfilled is True

    async def test_is_dismissed_reflects_dismissed_at(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)
        req = LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        db_session.add(req)
        await db_session.flush()

        assert req.is_dismissed is False
        req.dismissed_at = datetime(2025, 12, 1)
        assert req.is_dismissed is True

    async def test_label_from_batch_relationship(self, db_session: AsyncSession):
        project, batch = await _seed_context(db_session)
        req = LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        db_session.add(req)
        await db_session.flush()
        await db_session.refresh(req)

        assert req.label == batch.batch_num

    async def test_partial_unique_index_blocks_duplicate_active_rows(
        self, db_session: AsyncSession
    ):
        project, batch = await _seed_context(db_session)

        r1 = LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        db_session.add(r1)
        await db_session.flush()

        r2 = LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_partial_unique_index_allows_row_after_dismissal(
        self, db_session: AsyncSession
    ):
        project, batch = await _seed_context(db_session)

        r1 = LabReportRequirement(
            project_id=project.id,
            sample_batch_id=batch.id,
            dismissed_at=datetime(2025, 12, 1),
        )
        db_session.add(r1)
        await db_session.flush()

        r2 = LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        db_session.add(r2)
        await db_session.flush()  # should not raise
