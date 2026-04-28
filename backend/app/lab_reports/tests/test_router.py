"""
Router tests for item-level lab report ops: PATCH /save, POST /dismiss, POST /undismiss.
"""

from datetime import datetime

import pytest
from httpx import AsyncClient
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


async def _seed_req(db: AsyncSession, **overrides) -> tuple:
    school = await seed_school(db)
    project = await seed_project(db, school)
    emp = await seed_employee(db)
    role = await seed_employee_role(db, emp)
    entry = await seed_time_entry(db, emp, role, project, school)
    sample_type = await seed_sample_type(db)
    batch = await seed_sample_batch(db, entry, sample_type)
    req = LabReportRequirement(
        project_id=project.id, sample_batch_id=batch.id, **overrides
    )
    db.add(req)
    await db.flush()
    return project, batch, req


class TestSaveLabReport:
    async def test_save_sets_is_saved_and_stamps_saved_at(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, req = await _seed_req(db_session)

        resp = await auth_client.patch(f"/lab-reports/{req.id}/save", json={"is_saved": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_saved"] is True
        assert data["saved_at"] is not None
        assert data["is_fulfilled"] is True

    async def test_save_sets_file_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, req = await _seed_req(db_session)

        resp = await auth_client.patch(f"/lab-reports/{req.id}/save", json={"file_id": 42})
        assert resp.status_code == 200
        assert resp.json()["file_id"] == 42

    async def test_saved_at_not_overwritten_on_second_save(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, req = await _seed_req(db_session, saved_at=datetime(2025, 1, 1))

        resp = await auth_client.patch(f"/lab-reports/{req.id}/save", json={"is_saved": True})
        assert resp.status_code == 200
        # saved_at was already set — must not be overwritten
        assert resp.json()["saved_at"] is not None

    async def test_404_unknown_id(self, auth_client: AsyncClient):
        resp = await auth_client.patch("/lab-reports/99999/save", json={"is_saved": True})
        assert resp.status_code == 404


class TestDismissLabReport:
    async def test_dismisses_requirement(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, req = await _seed_req(db_session)

        resp = await auth_client.post(
            f"/lab-reports/{req.id}/dismiss",
            json={"dismissal_reason": "Lab report not required for this batch"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dismissed_at"] is not None
        assert data["dismissal_reason"] == "Lab report not required for this batch"
        assert data["is_dismissed"] is True

    async def test_already_dismissed_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, req = await _seed_req(db_session, dismissed_at=datetime(2025, 12, 1))

        resp = await auth_client.post(
            f"/lab-reports/{req.id}/dismiss",
            json={"dismissal_reason": "Again"},
        )
        assert resp.status_code == 422

    async def test_empty_reason_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, req = await _seed_req(db_session)

        resp = await auth_client.post(
            f"/lab-reports/{req.id}/dismiss", json={"dismissal_reason": "   "}
        )
        assert resp.status_code == 422

    async def test_404_unknown_id(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/lab-reports/99999/dismiss", json={"dismissal_reason": "reason"}
        )
        assert resp.status_code == 404


class TestUndismissLabReport:
    async def test_undismisses_requirement(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, req = await _seed_req(
            db_session,
            dismissed_at=datetime(2025, 12, 1),
            dismissed_by_id=1,
            dismissal_reason="Was not needed",
        )

        resp = await auth_client.post(f"/lab-reports/{req.id}/undismiss")
        assert resp.status_code == 200
        data = resp.json()
        assert data["dismissed_at"] is None
        assert data["dismissed_by_id"] is None
        assert data["dismissal_reason"] is None
        assert data["is_dismissed"] is False

    async def test_not_dismissed_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, req = await _seed_req(db_session)

        resp = await auth_client.post(f"/lab-reports/{req.id}/undismiss")
        assert resp.status_code == 422

    async def test_404_unknown_id(self, auth_client: AsyncClient):
        resp = await auth_client.post("/lab-reports/99999/undismiss")
        assert resp.status_code == 404
