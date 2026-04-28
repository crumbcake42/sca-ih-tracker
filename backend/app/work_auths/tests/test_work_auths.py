"""
Integration tests for work auth endpoints.

POST   /work-auths          — create
GET    /work-auths/{id}     — get by id
GET    /work-auths?project_id={id} — list filtered by project (paginated)
PATCH  /work-auths/{id}     — update
DELETE /work-auths/{id}     — delete
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.work_auths.models import WorkAuth
from tests.seeds import seed_project, seed_school, seed_work_auth

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wa_payload(**overrides) -> dict:
    defaults = dict(
        wa_num="WA-001",
        service_id="SVC-001",
        project_num="PN-001",
        initiation_date="2025-01-01",
    )
    return {**defaults, **overrides}


# ---------------------------------------------------------------------------
# POST /work-auths
# ---------------------------------------------------------------------------


class TestCreateWorkAuth:
    async def test_create_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        response = await auth_client.post(
            "/work-auths", json={**_wa_payload(), "project_id": project.id}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["wa_num"] == "WA-001"
        assert data["project_id"] == project.id

    async def test_missing_project_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/work-auths", json={**_wa_payload(), "project_id": 9999}
        )
        assert response.status_code == 404

    async def test_duplicate_project_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        await seed_work_auth(db_session, project)

        response = await auth_client.post(
            "/work-auths",
            json={
                **_wa_payload(
                    wa_num="WA-002", service_id="SVC-002", project_num="PN-002"
                ),
                "project_id": project.id,
            },
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# GET /work-auths/{id}
# ---------------------------------------------------------------------------


class TestGetWorkAuth:
    async def test_get_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        wa = await seed_work_auth(db_session, project, wa_num="WA-001")

        response = await auth_client.get(f"/work-auths/{wa.id}")
        assert response.status_code == 200
        assert response.json()["wa_num"] == "WA-001"

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/work-auths/9999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /work-auths?project_id={id}
# ---------------------------------------------------------------------------


class TestGetWorkAuthByProject:
    async def test_returns_paginated_list_for_project(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        await seed_work_auth(db_session, project, wa_num="WA-001")

        response = await auth_client.get(f"/work-auths?project_id={project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["project_id"] == project.id

    async def test_no_work_auth_returns_empty_list(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        response = await auth_client.get(f"/work-auths?project_id={project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


# ---------------------------------------------------------------------------
# PATCH /work-auths/{id}
# ---------------------------------------------------------------------------


class TestUpdateWorkAuth:
    async def test_update_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa = await seed_work_auth(db_session, project)

        response = await auth_client.patch(
            f"/work-auths/{wa.id}", json={"wa_num": "WA-UPDATED"}
        )
        assert response.status_code == 200
        assert response.json()["wa_num"] == "WA-UPDATED"

    async def test_update_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch("/work-auths/9999", json={"wa_num": "WA-X"})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /work-auths/{id}
# ---------------------------------------------------------------------------


class TestDeleteWorkAuth:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa = await seed_work_auth(db_session, project)

        response = await auth_client.delete(f"/work-auths/{wa.id}")
        assert response.status_code == 204

        follow_up = await auth_client.get(f"/work-auths/{wa.id}")
        assert follow_up.status_code == 404

    async def test_delete_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/work-auths/9999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Audit field wiring
# ---------------------------------------------------------------------------


class TestWorkAuthAuditFields:
    async def test_create_sets_created_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        response = await auth_client.post(
            "/work-auths",
            json={
                **_wa_payload(
                    wa_num="WA-AUDIT1", service_id="SVC-A1", project_num="PN-A1"
                ),
                "project_id": project.id,
            },
        )
        assert response.status_code == 201
        wa = await db_session.get(WorkAuth, response.json()["id"])
        assert wa and wa.created_by_id == 1  # fake_user.id from auth_client fixture

    async def test_update_sets_updated_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa = await seed_work_auth(db_session, project, wa_num="WA-AUDIT2")

        response = await auth_client.patch(
            f"/work-auths/{wa.id}", json={"wa_num": "WA-AUDIT2-UPDATED"}
        )
        assert response.status_code == 200
        await db_session.refresh(wa)
        assert wa.updated_by_id == 1  # fake_user.id from auth_client fixture
