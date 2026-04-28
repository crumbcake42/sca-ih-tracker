"""
Router tests for DEP filing form admin CRUD at /dep-filings/forms.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dep_filings.models import DEPFilingForm, ProjectDEPFiling
from tests.seeds import seed_project, seed_school


async def _seed_form(db: AsyncSession, code: str = "ICR", **overrides) -> DEPFilingForm:
    defaults = dict(code=code, label=f"{code} Filing", is_default_selected=True, display_order=1)
    defaults.update(overrides)
    form = DEPFilingForm(**defaults)
    db.add(form)
    await db.flush()
    return form


class TestListDEPFilingForms:
    async def test_returns_all_forms(self, auth_client: AsyncClient, db_session: AsyncSession):
        await _seed_form(db_session, "AAA")
        await _seed_form(db_session, "BBB")

        resp = await auth_client.get("/dep-filings/forms/?limit=50")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    async def test_sorted_by_display_order(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_form(db_session, "ZZZ", display_order=10)
        await _seed_form(db_session, "AAA2", display_order=1)

        resp = await auth_client.get("/dep-filings/forms/?limit=50")
        assert resp.status_code == 200
        codes = [item["code"] for item in resp.json()["items"]]
        # AAA2 (order=1) should come before ZZZ (order=10)
        assert codes.index("AAA2") < codes.index("ZZZ")


class TestGetDEPFilingForm:
    async def test_returns_form(self, auth_client: AsyncClient, db_session: AsyncSession):
        form = await _seed_form(db_session, "GET1")

        resp = await auth_client.get(f"/dep-filings/forms/{form.id}")
        assert resp.status_code == 200
        assert resp.json()["code"] == "GET1"

    async def test_404_unknown_id(self, auth_client: AsyncClient, db_session: AsyncSession):
        resp = await auth_client.get("/dep-filings/forms/99999")
        assert resp.status_code == 404


class TestCreateDEPFilingForm:
    async def test_creates_form(self, auth_client: AsyncClient, db_session: AsyncSession):
        resp = await auth_client.post(
            "/dep-filings/forms/",
            json={"code": "NEW1", "label": "New Form", "is_default_selected": False, "display_order": 5},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "NEW1"
        assert data["label"] == "New Form"
        assert data["display_order"] == 5

    async def test_duplicate_code_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_form(db_session, "DUP1")

        resp = await auth_client.post(
            "/dep-filings/forms/",
            json={"code": "DUP1", "label": "Duplicate"},
        )
        assert resp.status_code == 422


class TestUpdateDEPFilingForm:
    async def test_updates_label(self, auth_client: AsyncClient, db_session: AsyncSession):
        form = await _seed_form(db_session, "UPD1")

        resp = await auth_client.patch(
            f"/dep-filings/forms/{form.id}", json={"label": "Updated Label"}
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "Updated Label"

    async def test_code_change_to_duplicate_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        form1 = await _seed_form(db_session, "CD1")
        await _seed_form(db_session, "CD2")

        resp = await auth_client.patch(f"/dep-filings/forms/{form1.id}", json={"code": "CD2"})
        assert resp.status_code == 422

    async def test_404_unknown_id(self, auth_client: AsyncClient, db_session: AsyncSession):
        resp = await auth_client.patch("/dep-filings/forms/99999", json={"label": "X"})
        assert resp.status_code == 404


class TestDeleteDEPFilingForm:
    async def test_deletes_form_with_no_filings(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        form = await _seed_form(db_session, "DEL1")

        resp = await auth_client.delete(f"/dep-filings/forms/{form.id}")
        assert resp.status_code == 204

    async def test_guarded_delete_blocked_when_filings_exist(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "BLK1")

        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(filing)
        await db_session.flush()

        resp = await auth_client.delete(f"/dep-filings/forms/{form.id}")
        assert resp.status_code == 409

    async def test_connections_endpoint_counts_filings(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "CNX1")

        filing = ProjectDEPFiling(project_id=project.id, dep_filing_form_id=form.id)
        db_session.add(filing)
        await db_session.flush()

        resp = await auth_client.get(f"/dep-filings/forms/{form.id}/connections")
        assert resp.status_code == 200
        assert resp.json()["project_dep_filings"] == 1
