"""
Endpoint tests for GET /projects/{id}/status.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro, ProjectStatus
from app.projects.models import Project
from app.schools.models import School


async def _seed_school(db: AsyncSession) -> School:
    school = School(
        code="K200",
        name="Status Test School",
        address="200 Test St",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()
    return school


async def _seed_project(db: AsyncSession, school: School) -> Project:
    project = Project(name="Status Test Project", project_number="26-111-99")
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


class TestGetProjectStatus:
    async def test_404_for_unknown_project(self, auth_client: AsyncClient):
        response = await auth_client.get("/projects/9999/status")
        assert response.status_code == 404

    async def test_returns_status_shape(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        response = await auth_client.get(f"/projects/{project.id}/status")

        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == project.id
        assert body["status"] == ProjectStatus.SETUP
        assert body["has_work_auth"] is False
        assert body["pending_rfa_count"] == 0
        assert body["outstanding_deliverable_count"] == 0
        assert body["unconfirmed_time_entry_count"] == 0
        assert body["blocking_issues"] == []
