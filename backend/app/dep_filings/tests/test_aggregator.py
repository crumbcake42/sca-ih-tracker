"""
Aggregator integration tests for Silo 3.

Verifies that unfulfilled, undismissed ProjectDEPFiling rows surface through
get_unfulfilled_requirements_for_project, and that saved or dismissed rows do not.
"""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.requirements import get_unfulfilled_requirements_for_project
from app.dep_filings.models import DEPFilingForm, ProjectDEPFiling
from tests.seeds import seed_project, seed_school


async def _seed_project(db: AsyncSession):
    school = await seed_school(db)
    return await seed_project(db, school)


async def _seed_form(db: AsyncSession, code: str = "ICR", label: str | None = None) -> DEPFilingForm:
    form = DEPFilingForm(code=code, label=label or f"{code} Filing")
    db.add(form)
    await db.flush()
    return form


class TestAggregatorSilo3:
    async def test_unfulfilled_row_surfaces(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "AGG1")
        db_session.add(ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id))
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        dep_reqs = [r for r in results if r.requirement_type == "project_dep_filing"]
        assert len(dep_reqs) == 1
        assert dep_reqs[0].project_id == project.id

    async def test_saved_row_does_not_surface(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "AGG2")
        db_session.add(
            ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id, is_saved=True)
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        dep_reqs = [r for r in results if r.requirement_type == "project_dep_filing"]
        assert dep_reqs == []

    async def test_dismissed_row_does_not_surface(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "AGG3")
        db_session.add(
            ProjectDEPFiling(
                project_id=project.id,
                dep_filing_form_id=form.id,
                dismissed_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        dep_reqs = [r for r in results if r.requirement_type == "project_dep_filing"]
        assert dep_reqs == []

    async def test_unfulfilled_requirement_has_correct_shape(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        form = await _seed_form(db_session, "AGG4", label="My DEP Filing")
        db_session.add(ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id))
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        dep_reqs = [r for r in results if r.requirement_type == "project_dep_filing"]
        assert len(dep_reqs) == 1
        req = dep_reqs[0]
        assert req.requirement_type == "project_dep_filing"
        assert req.is_dismissable is True
        assert req.is_dismissed is False
        assert req.label == "My DEP Filing"
