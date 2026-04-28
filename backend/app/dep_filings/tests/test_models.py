"""
ORM model tests for DEPFilingForm and ProjectDEPFiling.

Verifies round-trip persistence, partial unique index behavior,
protocol property correctness, and AuditMixin/DismissibleMixin columns.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dep_filings.models import DEPFilingForm, ProjectDEPFiling
from tests.seeds import seed_project, seed_school


async def _seed_project(db: AsyncSession):
    school = await seed_school(db)
    return await seed_project(db, school)


async def _seed_form(db: AsyncSession, **overrides) -> DEPFilingForm:
    defaults = dict(code="ICR", label="ICR Filing", is_default_selected=True, display_order=1)
    defaults.update(overrides)
    form = DEPFilingForm(**defaults)
    db.add(form)
    await db.flush()
    return form


class TestDEPFilingFormModel:
    async def test_round_trip_insert(self, db_session: AsyncSession):
        form = await _seed_form(db_session)
        fetched = await db_session.get(DEPFilingForm, form.id)
        assert fetched is not None
        assert fetched.code == "ICR"
        assert fetched.label == "ICR Filing"
        assert fetched.is_default_selected is True
        assert fetched.display_order == 1

    async def test_audit_columns_populated(self, db_session: AsyncSession):
        form = await _seed_form(db_session, code="AHR")
        fetched = await db_session.get(DEPFilingForm, form.id)
        assert fetched.created_at is not None
        assert fetched.updated_at is not None

    async def test_code_unique_constraint(self, db_session: AsyncSession):
        await _seed_form(db_session, code="UNIQUE")
        form2 = DEPFilingForm(code="UNIQUE", label="Duplicate")
        db_session.add(form2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestProjectDEPFilingModel:
    async def test_round_trip_insert(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, code="ICR2")
        filing = ProjectDEPFiling(
            project_id=project.id,
            dep_filing_form_id=form.id,
            is_saved=False,
        )
        db_session.add(filing)
        await db_session.flush()

        fetched = await db_session.get(ProjectDEPFiling, filing.id)
        assert fetched is not None
        assert fetched.project_id == project.id
        assert fetched.dep_filing_form_id == form.id
        assert fetched.is_saved is False
        assert fetched.dismissed_at is None

    async def test_audit_columns_populated(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, code="AUD")
        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(filing)
        await db_session.flush()

        fetched = await db_session.get(ProjectDEPFiling, filing.id)
        assert fetched.created_at is not None
        assert fetched.updated_at is not None

    async def test_dismissible_columns_present(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, code="DISM")
        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(filing)
        await db_session.flush()

        fetched = await db_session.get(ProjectDEPFiling, filing.id)
        assert fetched.dismissal_reason is None
        assert fetched.dismissed_by_id is None
        assert fetched.dismissed_at is None

    async def test_is_fulfilled_reflects_is_saved(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, code="FULF")
        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id, is_saved=False)
        db_session.add(filing)
        await db_session.flush()

        assert filing.is_fulfilled is False
        filing.is_saved = True
        assert filing.is_fulfilled is True

    async def test_is_dismissed_reflects_dismissed_at(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, code="DISR")
        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(filing)
        await db_session.flush()

        assert filing.is_dismissed is False
        filing.dismissed_at = datetime(2025, 12, 1)
        assert filing.is_dismissed is True

    async def test_label_from_form_relationship(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, code="LBL", label="My Form Label")
        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(filing)
        await db_session.flush()
        await db_session.refresh(filing)

        assert filing.label == "My Form Label"

    async def test_partial_unique_index_blocks_duplicate_active_rows(
        self, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, code="UNIQ")

        f1 = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(f1)
        await db_session.flush()

        f2 = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(f2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_partial_unique_index_allows_row_after_dismissal(
        self, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, code="RMAT")

        f1 = ProjectDEPFiling(
            project_id=project.id,
            dep_filing_form_id=form.id,
            dismissed_at=datetime(2025, 12, 1),  # dismissed — not counted by partial index
        )
        db_session.add(f1)
        await db_session.flush()

        f2 = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(f2)
        await db_session.flush()  # should not raise
