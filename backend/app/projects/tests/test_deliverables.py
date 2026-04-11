"""
Integration tests for project deliverable endpoints.

GET    /projects/{id}/deliverables
POST   /projects/{id}/deliverables
PATCH  /projects/{id}/deliverables/{deliverable_id}
DELETE /projects/{id}/deliverables/{deliverable_id}

GET    /projects/{id}/building-deliverables
POST   /projects/{id}/building-deliverables
PATCH  /projects/{id}/building-deliverables/{deliverable_id}/{school_id}
DELETE /projects/{id}/building-deliverables/{deliverable_id}/{school_id}
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import (
    Boro,
    InternalDeliverableStatus,
    SCADeliverableStatus,
    WACodeLevel,
)
from app.deliverables.models import (
    Deliverable,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.projects.models import Project
from app.schools.models import School

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_school(db: AsyncSession, code: str = "K001") -> School:
    school = School(
        code=code,
        name=f"School {code}",
        address="123 Main St",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()
    return school


async def _seed_project(db: AsyncSession, school: School, number: str = "26-111-01") -> Project:
    project = Project(name="Test Project", project_number=number)
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


async def _seed_deliverable(
    db: AsyncSession,
    name: str = "Test Report",
    level: WACodeLevel = WACodeLevel.PROJECT,
) -> Deliverable:
    d = Deliverable(name=name, level=level)
    db.add(d)
    await db.flush()
    return d


# ---------------------------------------------------------------------------
# GET /projects/{id}/deliverables
# ---------------------------------------------------------------------------


class TestListProjectDeliverables:
    async def test_list_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session)
        db_session.add(ProjectDeliverable(project_id=project.id, deliverable_id=d.id))
        await db_session.flush()

        response = await auth_client.get(f"/projects/{project.id}/deliverables")
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_empty_list(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.get(f"/projects/{project.id}/deliverables")
        assert response.status_code == 200
        assert response.json() == []

    async def test_missing_project_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/projects/9999/deliverables")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /projects/{id}/deliverables
# ---------------------------------------------------------------------------


class TestAddProjectDeliverable:
    async def test_add_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session)

        response = await auth_client.post(
            f"/projects/{project.id}/deliverables",
            json={"deliverable_id": d.id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == project.id
        assert data["deliverable_id"] == d.id
        assert data["internal_status"] == InternalDeliverableStatus.INCOMPLETE
        assert data["sca_status"] == SCADeliverableStatus.PENDING_WA

    async def test_explicit_statuses_accepted(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session)

        response = await auth_client.post(
            f"/projects/{project.id}/deliverables",
            json={
                "deliverable_id": d.id,
                "internal_status": "in_review",
                "sca_status": "outstanding",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["internal_status"] == InternalDeliverableStatus.IN_REVIEW
        assert data["sca_status"] == SCADeliverableStatus.OUTSTANDING

    async def test_missing_deliverable_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.post(
            f"/projects/{project.id}/deliverables",
            json={"deliverable_id": 9999},
        )
        assert response.status_code == 404

    async def test_missing_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        d = await _seed_deliverable(db_session)
        response = await auth_client.post(
            "/projects/9999/deliverables",
            json={"deliverable_id": d.id},
        )
        assert response.status_code == 404

    async def test_duplicate_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session)
        db_session.add(ProjectDeliverable(project_id=project.id, deliverable_id=d.id))
        await db_session.flush()

        response = await auth_client.post(
            f"/projects/{project.id}/deliverables",
            json={"deliverable_id": d.id},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# PATCH /projects/{id}/deliverables/{deliverable_id}
# ---------------------------------------------------------------------------


class TestUpdateProjectDeliverable:
    async def test_update_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session)
        db_session.add(ProjectDeliverable(project_id=project.id, deliverable_id=d.id))
        await db_session.flush()

        response = await auth_client.patch(
            f"/projects/{project.id}/deliverables/{d.id}",
            json={"internal_status": "in_review", "notes": "Drafted, needs sign-off"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["internal_status"] == InternalDeliverableStatus.IN_REVIEW
        assert data["notes"] == "Drafted, needs sign-off"

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            "/projects/9999/deliverables/1",
            json={"internal_status": "completed"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /projects/{id}/deliverables/{deliverable_id}
# ---------------------------------------------------------------------------


class TestDeleteProjectDeliverable:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session)
        db_session.add(ProjectDeliverable(project_id=project.id, deliverable_id=d.id))
        await db_session.flush()

        response = await auth_client.delete(
            f"/projects/{project.id}/deliverables/{d.id}"
        )
        assert response.status_code == 204

        follow_up = await auth_client.get(f"/projects/{project.id}/deliverables")
        assert follow_up.json() == []

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/projects/9999/deliverables/1")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{id}/building-deliverables
# ---------------------------------------------------------------------------


class TestListBuildingDeliverables:
    async def test_list_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session, level=WACodeLevel.BUILDING)
        db_session.add(ProjectBuildingDeliverable(
            project_id=project.id, deliverable_id=d.id, school_id=school.id
        ))
        await db_session.flush()

        response = await auth_client.get(f"/projects/{project.id}/building-deliverables")
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_empty_list(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.get(f"/projects/{project.id}/building-deliverables")
        assert response.status_code == 200
        assert response.json() == []

    async def test_missing_project_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/projects/9999/building-deliverables")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /projects/{id}/building-deliverables
# ---------------------------------------------------------------------------


class TestAddBuildingDeliverable:
    async def test_add_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session, level=WACodeLevel.BUILDING)

        response = await auth_client.post(
            f"/projects/{project.id}/building-deliverables",
            json={"deliverable_id": d.id, "school_id": school.id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == project.id
        assert data["deliverable_id"] == d.id
        assert data["school_id"] == school.id
        assert data["internal_status"] == InternalDeliverableStatus.INCOMPLETE
        assert data["sca_status"] == SCADeliverableStatus.PENDING_WA

    async def test_school_not_on_project_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session, code="K001")
        other_school = await _seed_school(db_session, code="K002")
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session, level=WACodeLevel.BUILDING)

        response = await auth_client.post(
            f"/projects/{project.id}/building-deliverables",
            json={"deliverable_id": d.id, "school_id": other_school.id},
        )
        assert response.status_code == 422

    async def test_missing_deliverable_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.post(
            f"/projects/{project.id}/building-deliverables",
            json={"deliverable_id": 9999, "school_id": school.id},
        )
        assert response.status_code == 404

    async def test_missing_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        d = await _seed_deliverable(db_session, level=WACodeLevel.BUILDING)
        response = await auth_client.post(
            "/projects/9999/building-deliverables",
            json={"deliverable_id": d.id, "school_id": school.id},
        )
        assert response.status_code == 404

    async def test_duplicate_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session, level=WACodeLevel.BUILDING)
        db_session.add(ProjectBuildingDeliverable(
            project_id=project.id, deliverable_id=d.id, school_id=school.id
        ))
        await db_session.flush()

        response = await auth_client.post(
            f"/projects/{project.id}/building-deliverables",
            json={"deliverable_id": d.id, "school_id": school.id},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# PATCH /projects/{id}/building-deliverables/{deliverable_id}/{school_id}
# ---------------------------------------------------------------------------


class TestUpdateBuildingDeliverable:
    async def test_update_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session, level=WACodeLevel.BUILDING)
        db_session.add(ProjectBuildingDeliverable(
            project_id=project.id, deliverable_id=d.id, school_id=school.id
        ))
        await db_session.flush()

        response = await auth_client.patch(
            f"/projects/{project.id}/building-deliverables/{d.id}/{school.id}",
            json={"sca_status": "under_review", "notes": "Submitted to SCA"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sca_status"] == SCADeliverableStatus.UNDER_REVIEW
        assert data["notes"] == "Submitted to SCA"

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            "/projects/9999/building-deliverables/1/1",
            json={"internal_status": "completed"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /projects/{id}/building-deliverables/{deliverable_id}/{school_id}
# ---------------------------------------------------------------------------


class TestDeleteBuildingDeliverable:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        d = await _seed_deliverable(db_session, level=WACodeLevel.BUILDING)
        db_session.add(ProjectBuildingDeliverable(
            project_id=project.id, deliverable_id=d.id, school_id=school.id
        ))
        await db_session.flush()

        response = await auth_client.delete(
            f"/projects/{project.id}/building-deliverables/{d.id}/{school.id}"
        )
        assert response.status_code == 204

        follow_up = await auth_client.get(
            f"/projects/{project.id}/building-deliverables"
        )
        assert follow_up.json() == []

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete(
            "/projects/9999/building-deliverables/1/1"
        )
        assert response.status_code == 404
