"""
Integration tests for hygienist project assignment endpoints.

POST   /projects/{id}/hygienist  — assign (or replace) a hygienist
GET    /projects/{id}/hygienist  — read current assignment
DELETE /projects/{id}/hygienist  — remove assignment

The Project detail endpoint (GET /projects/{id}) is also tested to confirm
it correctly surfaces the hygienist field via the model_validator mapping.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.seeds import seed_school, seed_project, seed_hygienist


# ---------------------------------------------------------------------------
# POST /projects/{id}/hygienist
# ---------------------------------------------------------------------------


class TestAssignHygienist:
    async def test_assign_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        hygienist = await seed_hygienist(db_session)

        response = await auth_client.post(
            f"/projects/{project.id}/hygienist",
            json={"hygienist_id": hygienist.id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["hygienist_id"] == hygienist.id
        assert "assigned_at" in data

    async def test_assign_missing_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        hygienist = await seed_hygienist(db_session)
        response = await auth_client.post(
            "/projects/9999/hygienist",
            json={"hygienist_id": hygienist.id},
        )
        assert response.status_code == 404

    async def test_assign_missing_hygienist_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        response = await auth_client.post(
            f"/projects/{project.id}/hygienist",
            json={"hygienist_id": 9999},
        )
        assert response.status_code == 404

    async def test_reassign_replaces_existing(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # A second POST should update the assignment, not create a second row.
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        h1 = await seed_hygienist(db_session, first_name="Alice")
        h2 = await seed_hygienist(db_session, first_name="Bob")

        await auth_client.post(
            f"/projects/{project.id}/hygienist", json={"hygienist_id": h1.id}
        )
        response = await auth_client.post(
            f"/projects/{project.id}/hygienist", json={"hygienist_id": h2.id}
        )
        assert response.status_code == 201
        assert response.json()["hygienist_id"] == h2.id

        # Confirm only one assignment exists by fetching the detail endpoint.
        detail = await auth_client.get(f"/projects/{project.id}/hygienist")
        assert detail.json()["hygienist_id"] == h2.id


# ---------------------------------------------------------------------------
# GET /projects/{id}/hygienist
# ---------------------------------------------------------------------------


class TestGetHygienistAssignment:
    async def test_returns_assignment(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        hygienist = await seed_hygienist(db_session)

        await auth_client.post(
            f"/projects/{project.id}/hygienist",
            json={"hygienist_id": hygienist.id},
        )
        response = await auth_client.get(f"/projects/{project.id}/hygienist")
        assert response.status_code == 200
        assert response.json()["hygienist_id"] == hygienist.id

    async def test_unassigned_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        response = await auth_client.get(f"/projects/{project.id}/hygienist")
        assert response.status_code == 404

    async def test_missing_project_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/projects/9999/hygienist")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /projects/{id}/hygienist
# ---------------------------------------------------------------------------


class TestRemoveHygienistAssignment:
    async def test_remove_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        hygienist = await seed_hygienist(db_session)

        await auth_client.post(
            f"/projects/{project.id}/hygienist",
            json={"hygienist_id": hygienist.id},
        )
        response = await auth_client.delete(f"/projects/{project.id}/hygienist")
        assert response.status_code == 204

        # Confirm it's gone.
        follow_up = await auth_client.get(f"/projects/{project.id}/hygienist")
        assert follow_up.status_code == 404

    async def test_remove_unassigned_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        response = await auth_client.delete(f"/projects/{project.id}/hygienist")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{id} — hygienist field surfaced in project detail
# ---------------------------------------------------------------------------


class TestProjectDetailIncludesHygienist:
    async def test_hygienist_null_when_unassigned(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        response = await auth_client.get(f"/projects/{project.id}")
        assert response.status_code == 200
        assert response.json()["hygienist"] is None

    async def test_hygienist_present_when_assigned(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        hygienist = await seed_hygienist(db_session)

        await auth_client.post(
            f"/projects/{project.id}/hygienist",
            json={"hygienist_id": hygienist.id},
        )
        response = await auth_client.get(f"/projects/{project.id}")
        assert response.status_code == 200
        assert response.json()["hygienist"]["hygienist_id"] == hygienist.id
