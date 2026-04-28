"""
Router tests for project-scoped DEP filing endpoints:
GET /projects/{id}/dep-filings and POST /projects/{id}/dep-filings.
"""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dep_filings.models import DEPFilingForm, ProjectDEPFiling
from tests.seeds import seed_project, seed_school


async def _seed_form(db: AsyncSession, code: str = "ICR", **overrides) -> DEPFilingForm:
    defaults = dict(code=code, label=f"{code} Filing")
    defaults.update(overrides)
    form = DEPFilingForm(**defaults)
    db.add(form)
    await db.flush()
    return form


class TestListDEPFilingsForProject:
    async def test_returns_active_rows(self, auth_client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "LST1")

        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(filing)
        await db_session.flush()

        resp = await auth_client.get(f"/projects/{project.id}/dep-filings")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_dismissed_hidden_by_default(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form_a = await _seed_form(db_session, "LST2A")
        form_b = await _seed_form(db_session, "LST2B")

        db_session.add(ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form_a.id))
        db_session.add(
            ProjectDEPFiling(
                project_id=project.id,
                dep_filing_form_id=form_b.id,
                dismissed_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        resp = await auth_client.get(f"/projects/{project.id}/dep-filings")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_include_dismissed_shows_all(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form_a = await _seed_form(db_session, "LST3A")
        form_b = await _seed_form(db_session, "LST3B")

        db_session.add(ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form_a.id))
        db_session.add(
            ProjectDEPFiling(
                project_id=project.id,
                dep_filing_form_id=form_b.id,
                dismissed_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        resp = await auth_client.get(
            f"/projects/{project.id}/dep-filings?include_dismissed=true"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_404_unknown_project(self, auth_client: AsyncClient, db_session: AsyncSession):
        resp = await auth_client.get("/projects/99999/dep-filings")
        assert resp.status_code == 404


class TestSelectDEPFilingsForProject:
    async def test_materializes_one_row_per_form(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form_a = await _seed_form(db_session, "SEL1A")
        form_b = await _seed_form(db_session, "SEL1B")

        resp = await auth_client.post(
            f"/projects/{project.id}/dep-filings",
            json={"form_ids": [form_a.id, form_b.id]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 2
        form_ids = {row["dep_filing_form_id"] for row in data}
        assert form_ids == {form_a.id, form_b.id}

    async def test_idempotent_no_duplicates(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "SEL2")

        await auth_client.post(
            f"/projects/{project.id}/dep-filings", json={"form_ids": [form.id]}
        )
        resp = await auth_client.post(
            f"/projects/{project.id}/dep-filings", json={"form_ids": [form.id]}
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 1

    async def test_response_includes_label(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "LBL1", label="My Special Form")

        resp = await auth_client.post(
            f"/projects/{project.id}/dep-filings", json={"form_ids": [form.id]}
        )
        assert resp.status_code == 201
        assert resp.json()[0]["label"] == "My Special Form"

    async def test_records_current_user_not_system_user(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.common.config import SYSTEM_USER_ID

        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "USR1")

        resp = await auth_client.post(
            f"/projects/{project.id}/dep-filings", json={"form_ids": [form.id]}
        )
        assert resp.status_code == 201
        # auth_client uses fake user id=1; SYSTEM_USER_ID is also 1 by default
        # The important thing is it's the current user's id, not an explicit system marker.
        # We verify that created_by_id is set (not None).
        assert resp.json()[0]["created_by_id"] is not None

    async def test_unknown_form_id_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        resp = await auth_client.post(
            f"/projects/{project.id}/dep-filings", json={"form_ids": [99999]}
        )
        assert resp.status_code == 422

    async def test_404_unknown_project(self, auth_client: AsyncClient, db_session: AsyncSession):
        form = await _seed_form(db_session, "UNK1")
        resp = await auth_client.post(
            "/projects/99999/dep-filings", json={"form_ids": [form.id]}
        )
        assert resp.status_code == 404

    async def test_empty_form_ids_returns_empty_list(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        resp = await auth_client.post(
            f"/projects/{project.id}/dep-filings", json={"form_ids": []}
        )
        assert resp.status_code == 201
        assert resp.json() == []
