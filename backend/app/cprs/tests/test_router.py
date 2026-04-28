"""
Router tests for /projects/{id}/cprs and /cprs/{id}.
"""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cprs.models import ContractorPaymentRecord
from app.notes.models import Note
from app.projects.models import ProjectContractorLink
from tests.seeds import seed_contractor, seed_project, seed_school


async def _seed_project(db: AsyncSession):
    school = await seed_school(db)
    return await seed_project(db, school)


async def _seed_cpr(db: AsyncSession, project_id: int, contractor_id: int, **overrides) -> ContractorPaymentRecord:
    defaults = dict(
        project_id=project_id,
        contractor_id=contractor_id,
    )
    defaults.update(overrides)
    record = ContractorPaymentRecord(**defaults)
    db.add(record)
    await db.flush()
    return record


async def _seed_project_contractor_link(
    db: AsyncSession, project_id: int, contractor_id: int
) -> ProjectContractorLink:
    link = ProjectContractorLink(
        project_id=project_id, contractor_id=contractor_id, is_current=True
    )
    db.add(link)
    await db.flush()
    return link


class TestListContractorPaymentRecords:
    async def test_returns_active_rows(self, auth_client: AsyncClient, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor1 = await seed_contractor(db_session)
        contractor2 = await seed_contractor(db_session)
        await _seed_cpr(db_session, project.id, contractor1.id)
        await _seed_cpr(db_session, project.id, contractor2.id)

        resp = await auth_client.get(f"/projects/{project.id}/cprs")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_dismissed_hidden_by_default(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor1 = await seed_contractor(db_session)
        contractor2 = await seed_contractor(db_session)
        await _seed_cpr(db_session, project.id, contractor1.id)
        await _seed_cpr(
            db_session,
            project.id,
            contractor2.id,
            dismissed_at=datetime(2025, 12, 1),
            dismissal_reason="Not needed",
        )

        resp = await auth_client.get(f"/projects/{project.id}/cprs")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_include_dismissed_shows_all(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor1 = await seed_contractor(db_session)
        contractor2 = await seed_contractor(db_session)
        await _seed_cpr(db_session, project.id, contractor1.id)
        await _seed_cpr(
            db_session,
            project.id,
            contractor2.id,
            dismissed_at=datetime(2025, 12, 1),
            dismissal_reason="Not needed",
        )

        resp = await auth_client.get(
            f"/projects/{project.id}/cprs?include_dismissed=true"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_returns_404_for_unknown_project(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await auth_client.get("/projects/99999/cprs")
        assert resp.status_code == 404

    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        resp = await client.get(f"/projects/{project.id}/cprs")
        assert resp.status_code == 401


class TestCreateContractorPaymentRecord:
    async def test_manual_create_success(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        await _seed_project_contractor_link(db_session, project.id, contractor.id)

        resp = await auth_client.post(
            f"/projects/{project.id}/cprs",
            json={"project_id": project.id, "contractor_id": contractor.id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["contractor_id"] == contractor.id
        assert data["is_fulfilled"] is False
        assert data["rfp_saved_at"] is None

    async def test_project_id_mismatch_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        resp = await auth_client.post(
            f"/projects/{project.id}/cprs",
            json={"project_id": project.id + 1, "contractor_id": contractor.id},
        )
        assert resp.status_code == 422

    async def test_contractor_not_linked_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        # No link created

        resp = await auth_client.post(
            f"/projects/{project.id}/cprs",
            json={"project_id": project.id, "contractor_id": contractor.id},
        )
        assert resp.status_code == 422

    async def test_unknown_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        contractor = await seed_contractor(db_session)
        resp = await auth_client.post(
            "/projects/99999/cprs",
            json={"project_id": 99999, "contractor_id": contractor.id},
        )
        assert resp.status_code == 404


class TestUpdateContractorPaymentRecord:
    async def test_patch_rfp_saved_at_marks_fulfilled(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(db_session, project.id, contractor.id)

        resp = await auth_client.patch(
            f"/cprs/{record.id}",
            json={"rfp_saved_at": "2025-12-01T00:00:00"},
        )
        assert resp.status_code == 200
        assert resp.json()["rfp_saved_at"] is not None
        assert resp.json()["is_fulfilled"] is True

    async def test_patch_unknown_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await auth_client.patch(
            "/cprs/99999",
            json={"rfp_saved_at": "2025-12-01T00:00:00"},
        )
        assert resp.status_code == 404

    async def test_rfa_resubmission_emits_history_note(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(
            db_session,
            project.id,
            contractor.id,
            rfa_submitted_at=datetime(2025, 11, 1),
        )

        resp = await auth_client.patch(
            f"/cprs/{record.id}",
            json={"rfa_submitted_at": "2025-12-01T00:00:00"},
        )
        assert resp.status_code == 200

        notes = (
            await db_session.execute(
                select(Note).where(
                    Note.entity_id == record.id,
                )
            )
        ).scalars().all()
        assert len(notes) == 1
        assert "RFA re-submission" in notes[0].body
        assert notes[0].is_blocking is False
        assert notes[0].is_resolved is True

    async def test_rfa_first_submission_does_not_emit_note(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(db_session, project.id, contractor.id)

        resp = await auth_client.patch(
            f"/cprs/{record.id}",
            json={"rfa_submitted_at": "2025-12-01T00:00:00"},
        )
        assert resp.status_code == 200

        notes = (
            await db_session.execute(
                select(Note).where(Note.entity_id == record.id)
            )
        ).scalars().all()
        assert notes == []


class TestDismissContractorPaymentRecord:
    async def test_dismiss_sets_dismissal_fields(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(db_session, project.id, contractor.id)

        resp = await auth_client.post(
            f"/cprs/{record.id}/dismiss",
            json={"dismissal_reason": "Not applicable to this project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_dismissed"] is True
        assert data["dismissal_reason"] == "Not applicable to this project"
        assert data["dismissed_at"] is not None

    async def test_dismiss_already_dismissed_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(
            db_session,
            project.id,
            contractor.id,
            dismissed_at=datetime(2025, 12, 1),
            dismissal_reason="old",
        )

        resp = await auth_client.post(
            f"/cprs/{record.id}/dismiss",
            json={"dismissal_reason": "Again"},
        )
        assert resp.status_code == 422

    async def test_empty_dismissal_reason_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(db_session, project.id, contractor.id)

        resp = await auth_client.post(
            f"/cprs/{record.id}/dismiss",
            json={"dismissal_reason": "   "},
        )
        assert resp.status_code == 422


class TestDeleteContractorPaymentRecord:
    async def test_delete_pristine_record_succeeds(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(db_session, project.id, contractor.id)

        resp = await auth_client.delete(f"/cprs/{record.id}")
        assert resp.status_code == 204

    async def test_delete_rfa_submitted_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(
            db_session,
            project.id,
            contractor.id,
            rfa_submitted_at=datetime(2025, 11, 1),
        )

        resp = await auth_client.delete(f"/cprs/{record.id}")
        assert resp.status_code == 422

    async def test_delete_rfp_submitted_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)
        record = await _seed_cpr(
            db_session,
            project.id,
            contractor.id,
            rfp_submitted_at=datetime(2025, 11, 15),
        )

        resp = await auth_client.delete(f"/cprs/{record.id}")
        assert resp.status_code == 422

    async def test_delete_unknown_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await auth_client.delete("/cprs/99999")
        assert resp.status_code == 404
