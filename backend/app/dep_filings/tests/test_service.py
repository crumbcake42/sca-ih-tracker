"""
Service tests for dep_filings: materialize_for_form_selection and handler classmethods.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dep_filings.models import DEPFilingForm, ProjectDEPFiling
from app.dep_filings.service import ProjectDEPFilingHandler, materialize_for_form_selection
from tests.seeds import seed_project, seed_school

FAKE_USER_ID = 42


async def _seed_project(db: AsyncSession):
    school = await seed_school(db)
    return await seed_project(db, school)


async def _seed_form(db: AsyncSession, code: str = "ICR", **overrides) -> DEPFilingForm:
    form = DEPFilingForm(code=code, label=f"{code} Filing", **overrides)
    db.add(form)
    await db.flush()
    return form


class TestMaterializeForFormSelection:
    async def test_creates_one_row_per_form(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form_a = await _seed_form(db_session, "AAA")
        form_b = await _seed_form(db_session, "BBB")

        rows = await materialize_for_form_selection(
            project.id, [form_a.id, form_b.id], FAKE_USER_ID, db_session
        )
        await db_session.flush()

        assert len(rows) == 2
        ids = {r.dep_filing_form_id for r in rows}
        assert ids == {form_a.id, form_b.id}

    async def test_idempotent_skips_existing_live_row(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "IDEM")

        await materialize_for_form_selection(project.id, [form.id], FAKE_USER_ID, db_session)
        await db_session.flush()
        await materialize_for_form_selection(project.id, [form.id], FAKE_USER_ID, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ProjectDEPFiling).where(ProjectDEPFiling.project_id == project.id)
            )
        ).scalars().all()
        assert len(rows) == 1

    async def test_records_current_user_id(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "USR")

        rows = await materialize_for_form_selection(
            project.id, [form.id], FAKE_USER_ID, db_session
        )
        await db_session.flush()
        assert rows[0].created_by_id == FAKE_USER_ID

    async def test_dismissed_row_does_not_block_new_row(self, db_session: AsyncSession):
        from datetime import datetime

        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "RMAT")

        # Create a dismissed row for the same (project, form)
        dismissed = ProjectDEPFiling(
            project_id=project.id,
            dep_filing_form_id=form.id,
            dismissed_at=datetime(2025, 12, 1),
        )
        db_session.add(dismissed)
        await db_session.flush()

        rows = await materialize_for_form_selection(
            project.id, [form.id], FAKE_USER_ID, db_session
        )
        await db_session.flush()

        assert len(rows) == 1
        assert rows[0].id != dismissed.id

    async def test_empty_form_ids_returns_empty_list(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        rows = await materialize_for_form_selection(project.id, [], FAKE_USER_ID, db_session)
        assert rows == []


class TestGetUnfulfilledForProject:
    async def test_returns_unsaved_undismissed_rows(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "UNFL")

        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id, is_saved=False)
        db_session.add(filing)
        await db_session.flush()

        result = await ProjectDEPFilingHandler.get_unfulfilled_for_project(project.id, db_session)
        assert len(result) == 1
        assert result[0].id == filing.id

    async def test_excludes_saved_rows(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "SAVD")

        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id, is_saved=True)
        db_session.add(filing)
        await db_session.flush()

        result = await ProjectDEPFilingHandler.get_unfulfilled_for_project(project.id, db_session)
        assert result == []

    async def test_excludes_dismissed_rows(self, db_session: AsyncSession):
        from datetime import datetime

        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "DISM2")

        filing = ProjectDEPFiling(
            project_id=project.id,
            dep_filing_form_id=form.id,
            dismissed_at=datetime(2025, 12, 1),
        )
        db_session.add(filing)
        await db_session.flush()

        result = await ProjectDEPFilingHandler.get_unfulfilled_for_project(project.id, db_session)
        assert result == []


class TestValidateTemplateParams:
    def test_empty_dict_is_valid(self):
        ProjectDEPFilingHandler.validate_template_params({})

    def test_non_empty_dict_raises(self):
        with pytest.raises(ValueError, match="not configurable via requirement-triggers"):
            ProjectDEPFilingHandler.validate_template_params({"key": "value"})
