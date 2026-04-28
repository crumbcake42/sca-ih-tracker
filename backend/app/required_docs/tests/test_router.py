"""
Router tests for /projects/{id}/document-requirements and /document-requirements/{id}.
"""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import DocumentType
from app.required_docs.models import ProjectDocumentRequirement
from tests.seeds import seed_project, seed_school


async def _seed_project(db: AsyncSession):
    school = await seed_school(db)
    return await seed_project(db, school)


async def _seed_req(db: AsyncSession, project_id: int, **overrides) -> ProjectDocumentRequirement:
    defaults = dict(
        project_id=project_id,
        document_type=DocumentType.REOCCUPANCY_LETTER,
        is_saved=False,
        is_placeholder=False,
    )
    defaults.update(overrides)
    req = ProjectDocumentRequirement(**defaults)
    db.add(req)
    await db.flush()
    return req


class TestListDocumentRequirements:
    async def test_returns_active_rows(self, auth_client: AsyncClient, db_session: AsyncSession):
        project = await _seed_project(db_session)
        await _seed_req(db_session, project.id, document_type=DocumentType.DAILY_LOG)
        await _seed_req(db_session, project.id, document_type=DocumentType.MINOR_LETTER)

        resp = await auth_client.get(f"/projects/{project.id}/document-requirements")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_dismissed_hidden_by_default(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        await _seed_req(db_session, project.id, document_type=DocumentType.DAILY_LOG)
        await _seed_req(
            db_session,
            project.id,
            document_type=DocumentType.MINOR_LETTER,
            dismissed_at=datetime(2025, 12, 1),
        )

        resp = await auth_client.get(f"/projects/{project.id}/document-requirements")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["document_type"] == "daily_log"

    async def test_include_dismissed_shows_all(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        await _seed_req(db_session, project.id, document_type=DocumentType.DAILY_LOG)
        await _seed_req(
            db_session,
            project.id,
            document_type=DocumentType.MINOR_LETTER,
            dismissed_at=datetime(2025, 12, 1),
        )

        resp = await auth_client.get(
            f"/projects/{project.id}/document-requirements?include_dismissed=true"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_filter_by_document_type(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        await _seed_req(db_session, project.id, document_type=DocumentType.DAILY_LOG)
        await _seed_req(db_session, project.id, document_type=DocumentType.MINOR_LETTER)

        resp = await auth_client.get(
            f"/projects/{project.id}/document-requirements?document_type=daily_log"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["document_type"] == "daily_log"

    async def test_returns_404_for_unknown_project(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await auth_client.get("/projects/99999/document-requirements")
        assert resp.status_code == 404

    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        resp = await client.get(f"/projects/{project.id}/document-requirements")
        assert resp.status_code == 401


class TestCreateDocumentRequirement:
    async def test_manual_create_reoccupancy_letter(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        resp = await auth_client.post(
            f"/projects/{project.id}/document-requirements",
            json={"project_id": project.id, "document_type": "reoccupancy_letter"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_type"] == "reoccupancy_letter"
        assert data["is_saved"] is False
        assert data["label"] == "Re-Occupancy Letter"
        assert data["is_fulfilled"] is False

    async def test_project_id_mismatch_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        resp = await auth_client.post(
            f"/projects/{project.id}/document-requirements",
            json={"project_id": project.id + 1, "document_type": "minor_letter"},
        )
        assert resp.status_code == 422

    async def test_unknown_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await auth_client.post(
            "/projects/99999/document-requirements",
            json={"project_id": 99999, "document_type": "minor_letter"},
        )
        assert resp.status_code == 404


class TestUpdateDocumentRequirement:
    async def test_patch_is_saved_marks_fulfilled(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        req = await _seed_req(db_session, project.id)

        resp = await auth_client.patch(
            f"/document-requirements/{req.id}", json={"is_saved": True}
        )
        assert resp.status_code == 200
        assert resp.json()["is_saved"] is True
        assert resp.json()["is_fulfilled"] is True

    async def test_patch_unknown_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await auth_client.patch("/document-requirements/99999", json={"is_saved": True})
        assert resp.status_code == 404


class TestDismissDocumentRequirement:
    async def test_dismiss_sets_dismissal_fields(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        req = await _seed_req(db_session, project.id)

        resp = await auth_client.post(
            f"/document-requirements/{req.id}/dismiss",
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
        req = await _seed_req(
            db_session, project.id, dismissed_at=datetime(2025, 12, 1), dismissal_reason="old"
        )

        resp = await auth_client.post(
            f"/document-requirements/{req.id}/dismiss",
            json={"dismissal_reason": "Again"},
        )
        assert resp.status_code == 422

    async def test_empty_dismissal_reason_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        req = await _seed_req(db_session, project.id)

        resp = await auth_client.post(
            f"/document-requirements/{req.id}/dismiss",
            json={"dismissal_reason": "   "},
        )
        assert resp.status_code == 422


class TestDeleteDocumentRequirement:
    async def test_delete_unsaved_placeholder_succeeds(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        req = await _seed_req(db_session, project.id, is_placeholder=True, is_saved=False)

        resp = await auth_client.delete(f"/document-requirements/{req.id}")
        assert resp.status_code == 204

    async def test_delete_non_placeholder_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        req = await _seed_req(db_session, project.id, is_placeholder=False)

        resp = await auth_client.delete(f"/document-requirements/{req.id}")
        assert resp.status_code == 422

    async def test_delete_saved_placeholder_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        req = await _seed_req(db_session, project.id, is_placeholder=True, is_saved=True)

        resp = await auth_client.delete(f"/document-requirements/{req.id}")
        assert resp.status_code == 422

    async def test_delete_unknown_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await auth_client.delete("/document-requirements/99999")
        assert resp.status_code == 404
