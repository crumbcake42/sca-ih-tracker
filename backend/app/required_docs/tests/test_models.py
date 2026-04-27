"""
ORM model tests for ProjectDocumentRequirement.

Verifies round-trip persistence, partial unique index behavior,
and AuditMixin population.
"""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import DocumentType
from app.required_docs.models import ProjectDocumentRequirement
from tests.seeds import seed_employee, seed_project, seed_school

async def _seed_project(db):
    school = await seed_school(db)
    return await seed_project(db, school)


class TestProjectDocumentRequirementModel:
    async def test_round_trip_insert_and_select(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        req = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.DAILY_LOG,
            is_required=True,
            is_saved=False,
        )
        db_session.add(req)
        await db_session.flush()

        fetched = await db_session.get(ProjectDocumentRequirement, req.id)
        assert fetched is not None
        assert fetched.project_id == project.id
        assert fetched.document_type == DocumentType.DAILY_LOG
        assert fetched.is_saved is False
        assert fetched.dismissed_at is None

    async def test_audit_mixin_columns_populated(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        req = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.MINOR_LETTER,
            is_required=True,
            is_saved=False,
        )
        db_session.add(req)
        await db_session.flush()

        fetched = await db_session.get(ProjectDocumentRequirement, req.id)
        assert fetched.created_at is not None
        assert fetched.updated_at is not None

    async def test_dismissible_mixin_columns_present(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        req = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.REOCCUPANCY_LETTER,
            is_required=True,
            is_saved=False,
        )
        db_session.add(req)
        await db_session.flush()

        fetched = await db_session.get(ProjectDocumentRequirement, req.id)
        assert fetched.dismissal_reason is None
        assert fetched.dismissed_by_id is None
        assert fetched.dismissed_at is None

    async def test_partial_unique_index_blocks_duplicate_active_rows(
        self, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        employee = await seed_employee(db_session)
        school = await seed_school(db_session)
        entry_date = date(2025, 11, 30)

        r1 = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.DAILY_LOG,
            is_required=True,
            is_saved=False,
            employee_id=employee.id,
            date=entry_date,
            school_id=school.id,
        )
        db_session.add(r1)
        await db_session.flush()

        r2 = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.DAILY_LOG,
            is_required=True,
            is_saved=False,
            employee_id=employee.id,
            date=entry_date,
            school_id=school.id,
        )
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_partial_unique_index_allows_row_after_dismissal(
        self, db_session: AsyncSession
    ):
        from datetime import datetime

        project = await _seed_project(db_session)
        employee = await seed_employee(db_session)
        school = await seed_school(db_session)
        entry_date = date(2025, 11, 30)

        r1 = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.DAILY_LOG,
            is_required=True,
            is_saved=False,
            employee_id=employee.id,
            date=entry_date,
            school_id=school.id,
            dismissed_at=datetime(2025, 12, 1),  # dismissed — not counted by partial index
        )
        db_session.add(r1)
        await db_session.flush()

        r2 = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.DAILY_LOG,
            is_required=True,
            is_saved=False,
            employee_id=employee.id,
            date=entry_date,
            school_id=school.id,
        )
        db_session.add(r2)
        await db_session.flush()  # should not raise
