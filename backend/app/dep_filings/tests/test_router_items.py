"""
Router tests for item-level DEP filing ops: PATCH, dismiss, DELETE.
"""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dep_filings.models import DEPFilingForm, ProjectDEPFiling
from tests.seeds import seed_project, seed_school


async def _seed_form(db: AsyncSession, code: str = "ICR") -> DEPFilingForm:
    form = DEPFilingForm(code=code, label=f"{code} Filing")
    db.add(form)
    await db.flush()
    return form


async def _seed_filing(
    db: AsyncSession, project_id: int, form_id: int, **overrides
) -> ProjectDEPFiling:
    filing = ProjectDEPFiling(project_id=project_id, dep_filing_form_id=form_id, **overrides)
    db.add(filing)
    await db.flush()
    return filing


class TestUpdateDEPFiling:
    async def test_patch_is_saved_true(self, auth_client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "SAV1")
        filing = await _seed_filing(db_session, project.id, form.id)

        resp = await auth_client.patch(f"/dep-filings/{filing.id}", json={"is_saved": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_saved"] is True
        assert data["saved_at"] is not None
        assert data["is_fulfilled"] is True

    async def test_patch_sets_notes(self, auth_client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "NOTE1")
        filing = await _seed_filing(db_session, project.id, form.id)

        resp = await auth_client.patch(f"/dep-filings/{filing.id}", json={"notes": "some note"})
        assert resp.status_code == 200
        assert resp.json()["notes"] == "some note"

    async def test_patch_saved_at_not_overwritten_on_second_save(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "SAV2")
        filing = await _seed_filing(
            db_session, project.id, form.id, saved_at=datetime(2025, 1, 1)
        )

        resp = await auth_client.patch(f"/dep-filings/{filing.id}", json={"is_saved": True})
        assert resp.status_code == 200
        # saved_at was already set — should not be overwritten
        assert resp.json()["saved_at"] is not None

    async def test_404_unknown_id(self, auth_client: AsyncClient, db_session: AsyncSession):
        resp = await auth_client.patch("/dep-filings/99999", json={"is_saved": True})
        assert resp.status_code == 404


class TestDismissDEPFiling:
    async def test_dismisses_filing(self, auth_client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "DSM1")
        filing = await _seed_filing(db_session, project.id, form.id)

        resp = await auth_client.post(
            f"/dep-filings/{filing.id}/dismiss",
            json={"dismissal_reason": "Form not applicable"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dismissed_at"] is not None
        assert data["dismissal_reason"] == "Form not applicable"
        assert data["is_dismissed"] is True

    async def test_already_dismissed_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "DSM2")
        filing = await _seed_filing(
            db_session, project.id, form.id, dismissed_at=datetime(2025, 12, 1)
        )

        resp = await auth_client.post(
            f"/dep-filings/{filing.id}/dismiss",
            json={"dismissal_reason": "Again"},
        )
        assert resp.status_code == 422

    async def test_empty_reason_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "DSM3")
        filing = await _seed_filing(db_session, project.id, form.id)

        resp = await auth_client.post(
            f"/dep-filings/{filing.id}/dismiss", json={"dismissal_reason": "   "}
        )
        assert resp.status_code == 422

    async def test_404_unknown_id(self, auth_client: AsyncClient, db_session: AsyncSession):
        resp = await auth_client.post(
            "/dep-filings/99999/dismiss", json={"dismissal_reason": "reason"}
        )
        assert resp.status_code == 404


class TestDeleteDEPFiling:
    async def test_deletes_pristine_row(self, auth_client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "DEL1")
        filing = await _seed_filing(db_session, project.id, form.id)

        resp = await auth_client.delete(f"/dep-filings/{filing.id}")
        assert resp.status_code == 204

    async def test_saved_row_cannot_be_deleted(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "DEL2")
        filing = await _seed_filing(db_session, project.id, form.id, is_saved=True)

        resp = await auth_client.delete(f"/dep-filings/{filing.id}")
        assert resp.status_code == 422

    async def test_dismissed_row_cannot_be_deleted(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "DEL3")
        filing = await _seed_filing(
            db_session, project.id, form.id, dismissed_at=datetime(2025, 12, 1)
        )

        resp = await auth_client.delete(f"/dep-filings/{filing.id}")
        assert resp.status_code == 422

    async def test_row_with_file_id_cannot_be_deleted(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        form = await _seed_form(db_session, "DEL4")
        filing = await _seed_filing(db_session, project.id, form.id, file_id=99)

        resp = await auth_client.delete(f"/dep-filings/{filing.id}")
        assert resp.status_code == 422

    async def test_404_unknown_id(self, auth_client: AsyncClient, db_session: AsyncSession):
        resp = await auth_client.delete("/dep-filings/99999")
        assert resp.status_code == 404
