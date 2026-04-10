"""
Integration tests for work auth endpoints.

POST   /work-auths          — create
GET    /work-auths/{id}     — get by id
GET    /work-auths?project_id={id} — get for project
PATCH  /work-auths/{id}     — update
DELETE /work-auths/{id}     — delete
"""

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro
from app.projects.models import Project
from app.schools.models import School
from app.work_auths.models import WorkAuth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_school(db: AsyncSession) -> School:
    school = School(
        code="K001",
        name="Test School",
        address="123 Main St",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()
    return school


async def _seed_project(db: AsyncSession, school: School) -> Project:
    project = Project(name="Test Project", project_number="26-111-01")
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


async def _seed_work_auth(db: AsyncSession, project: Project, **overrides) -> WorkAuth:
    defaults = dict(
        wa_num="WA-001",
        service_id="SVC-001",
        project_num="PN-001",
        initiation_date=date(2025, 1, 1),
        project_id=project.id,
    )
    wa = WorkAuth(**{**defaults, **overrides})
    db.add(wa)
    await db.flush()
    return wa


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
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

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
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        await _seed_work_auth(db_session, project)

        response = await auth_client.post(
            "/work-auths",
            json={
                **_wa_payload(wa_num="WA-002", service_id="SVC-002", project_num="PN-002"),
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
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)

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
    async def test_returns_work_auth_for_project(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        await _seed_work_auth(db_session, project)

        response = await auth_client.get(f"/work-auths?project_id={project.id}")
        assert response.status_code == 200
        assert response.json()["project_id"] == project.id

    async def test_no_work_auth_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.get(f"/work-auths?project_id={project.id}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /work-auths/{id}
# ---------------------------------------------------------------------------


class TestUpdateWorkAuth:
    async def test_update_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)

        response = await auth_client.patch(
            f"/work-auths/{wa.id}", json={"wa_num": "WA-UPDATED"}
        )
        assert response.status_code == 200
        assert response.json()["wa_num"] == "WA-UPDATED"

    async def test_update_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            "/work-auths/9999", json={"wa_num": "WA-X"}
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /work-auths/{id}
# ---------------------------------------------------------------------------


class TestDeleteWorkAuth:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)

        response = await auth_client.delete(f"/work-auths/{wa.id}")
        assert response.status_code == 204

        follow_up = await auth_client.get(f"/work-auths/{wa.id}")
        assert follow_up.status_code == 404

    async def test_delete_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/work-auths/9999")
        assert response.status_code == 404
