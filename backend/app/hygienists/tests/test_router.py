"""
Integration tests for the hygienists router.

GET    /hygienists/{hygienist_id}/connections
DELETE /hygienists/{hygienist_id}
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro
from app.hygienists.models import Hygienist
from app.projects.models import Project
from app.projects.models.links import ProjectHygienistLink
from app.schools.models import School


def _make_hygienist(**overrides) -> Hygienist:
    defaults = dict(first_name="Alice", last_name="Hygienist")
    return Hygienist(**{**defaults, **overrides})


async def _seed(db: AsyncSession, *objs) -> list:
    for obj in objs:
        db.add(obj)
    await db.flush()
    return list(objs)


async def _seed_project_with_hygienist(
    db: AsyncSession, hygienist: Hygienist, project_number: str
) -> Project:
    school = School(
        code=f"H{project_number[-3:]}",
        name=f"School {project_number}",
        address="1 Main St",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()

    project = Project(name="Hygienist Project", project_number=project_number)
    project.schools = [school]
    db.add(project)
    await db.flush()

    db.add(ProjectHygienistLink(project_id=project.id, hygienist_id=hygienist.id))
    await db.flush()
    return project


# ---------------------------------------------------------------------------
# GET /hygienists/{hygienist_id}/connections
# ---------------------------------------------------------------------------


class TestGetHygienistConnections:
    async def test_clean_entity_returns_zero_counts(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [hygienist] = await _seed(db_session, _make_hygienist())
        response = await auth_client.get(f"/hygienists/{hygienist.id}/connections")
        assert response.status_code == 200
        assert response.json()["project_hygienist_links"] == 0

    async def test_counts_reflect_existing_references(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [hygienist] = await _seed(db_session, _make_hygienist())
        await _seed_project_with_hygienist(db_session, hygienist, "26-CONN-H001")

        response = await auth_client.get(f"/hygienists/{hygienist.id}/connections")
        assert response.status_code == 200
        assert response.json()["project_hygienist_links"] == 1

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/hygienists/9999/connections")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /hygienists/{hygienist_id}
# ---------------------------------------------------------------------------


class TestDeleteHygienist:
    async def test_clean_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [hygienist] = await _seed(db_session, _make_hygienist())
        response = await auth_client.delete(f"/hygienists/{hygienist.id}")
        assert response.status_code == 204

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/hygienists/9999")
        assert response.status_code == 404

    async def test_blocked_by_project_link_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [hygienist] = await _seed(db_session, _make_hygienist())
        await _seed_project_with_hygienist(db_session, hygienist, "26-DEL-H001")

        response = await auth_client.delete(f"/hygienists/{hygienist.id}")
        assert response.status_code == 409
        assert "project_hygienist_links" in response.json()["detail"]["blocked_by"]
