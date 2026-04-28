"""
Endpoint tests for GET /projects/{id}/status.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ProjectStatus
from tests.seeds import seed_project, seed_school


class TestGetProjectStatus:
    async def test_404_for_unknown_project(self, auth_client: AsyncClient):
        response = await auth_client.get("/projects/9999/status")
        assert response.status_code == 404

    async def test_returns_status_shape(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        response = await auth_client.get(f"/projects/{project.id}/status")

        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == project.id
        assert body["status"] == ProjectStatus.SETUP
        assert body["has_work_auth"] is False
        assert body["pending_rfa_count"] == 0
        assert body["outstanding_deliverable_count"] == 0
        assert body["unconfirmed_time_entry_count"] == 0
        assert body["unfulfilled_requirement_count"] == 0
        assert body["blocking_issues"] == []
