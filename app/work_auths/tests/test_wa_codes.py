"""
Integration tests for work auth project/building code endpoints.

POST   /work-auths/{id}/project-codes
GET    /work-auths/{id}/project-codes
PATCH  /work-auths/{id}/project-codes/{wa_code_id}
DELETE /work-auths/{id}/project-codes/{wa_code_id}

POST   /work-auths/{id}/building-codes
GET    /work-auths/{id}/building-codes
PATCH  /work-auths/{id}/building-codes/{wa_code_id}/{school_id}
DELETE /work-auths/{id}/building-codes/{wa_code_id}/{school_id}
"""

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro, WACodeLevel, WACodeStatus
from app.projects.models import Project
from app.schools.models import School
from app.wa_codes.models import WACode
from app.work_auths.models import WorkAuth, WorkAuthBuildingCode, WorkAuthProjectCode

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


async def _seed_work_auth(db: AsyncSession, project: Project) -> WorkAuth:
    wa = WorkAuth(
        wa_num="WA-001",
        service_id="SVC-001",
        project_num="PN-001",
        initiation_date=date(2025, 1, 1),
        project_id=project.id,
    )
    db.add(wa)
    await db.flush()
    return wa


async def _seed_wa_code(
    db: AsyncSession,
    code: str = "P-001",
    level: WACodeLevel = WACodeLevel.PROJECT,
    default_fee: str | None = None,
) -> WACode:
    wac = WACode(code=code, description=f"Description for {code}", level=level, default_fee=default_fee)
    db.add(wac)
    await db.flush()
    return wac


# ---------------------------------------------------------------------------
# POST /work-auths/{id}/project-codes
# ---------------------------------------------------------------------------


class TestAddProjectCode:
    async def test_add_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/project-codes",
            json={"wa_code_id": wac.id, "fee": "500.00"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["wa_code_id"] == wac.id
        assert data["fee"] == "500.00"
        assert data["status"] == WACodeStatus.RFA_NEEDED

    async def test_building_level_code_rejected(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/project-codes",
            json={"wa_code_id": wac.id, "fee": "100.00"},
        )
        assert response.status_code == 422

    async def test_missing_wa_code_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/project-codes",
            json={"wa_code_id": 9999, "fee": "100.00"},
        )
        assert response.status_code == 404

    async def test_duplicate_code_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)

        await auth_client.post(
            f"/work-auths/{wa.id}/project-codes",
            json={"wa_code_id": wac.id, "fee": "500.00"},
        )
        response = await auth_client.post(
            f"/work-auths/{wa.id}/project-codes",
            json={"wa_code_id": wac.id, "fee": "500.00"},
        )
        assert response.status_code == 409

    async def test_missing_work_auth_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/work-auths/9999/project-codes",
            json={"wa_code_id": 1, "fee": "100.00"},
        )
        assert response.status_code == 404

    async def test_omitted_fee_uses_default(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT, default_fee="350.00")

        response = await auth_client.post(
            f"/work-auths/{wa.id}/project-codes",
            json={"wa_code_id": wac.id},
        )
        assert response.status_code == 201
        assert response.json()["fee"] == "350.00"

    async def test_explicit_fee_overrides_default(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT, default_fee="350.00")

        response = await auth_client.post(
            f"/work-auths/{wa.id}/project-codes",
            json={"wa_code_id": wac.id, "fee": "999.00"},
        )
        assert response.status_code == 201
        assert response.json()["fee"] == "999.00"

    async def test_omitted_fee_no_default_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT, default_fee=None)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/project-codes",
            json={"wa_code_id": wac.id},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /work-auths/{id}/project-codes
# ---------------------------------------------------------------------------


class TestListProjectCodes:
    async def test_list_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)
        db_session.add(WorkAuthProjectCode(work_auth_id=wa.id, wa_code_id=wac.id, fee="200.00", status=WACodeStatus.ACTIVE))
        await db_session.flush()

        response = await auth_client.get(f"/work-auths/{wa.id}/project-codes")
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_empty_list(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)

        response = await auth_client.get(f"/work-auths/{wa.id}/project-codes")
        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# PATCH /work-auths/{id}/project-codes/{wa_code_id}
# ---------------------------------------------------------------------------


class TestUpdateProjectCode:
    async def test_update_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)
        db_session.add(WorkAuthProjectCode(work_auth_id=wa.id, wa_code_id=wac.id, fee="200.00", status=WACodeStatus.RFA_NEEDED))
        await db_session.flush()

        response = await auth_client.patch(
            f"/work-auths/{wa.id}/project-codes/{wac.id}",
            json={"status": "active", "fee": "750.00"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == WACodeStatus.ACTIVE
        assert data["fee"] == "750.00"

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            "/work-auths/9999/project-codes/1",
            json={"status": "active"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /work-auths/{id}/project-codes/{wa_code_id}
# ---------------------------------------------------------------------------


class TestDeleteProjectCode:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)
        db_session.add(WorkAuthProjectCode(work_auth_id=wa.id, wa_code_id=wac.id, fee="200.00", status=WACodeStatus.ACTIVE))
        await db_session.flush()

        response = await auth_client.delete(f"/work-auths/{wa.id}/project-codes/{wac.id}")
        assert response.status_code == 204

        follow_up = await auth_client.get(f"/work-auths/{wa.id}/project-codes")
        assert follow_up.json() == []

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/work-auths/9999/project-codes/1")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /work-auths/{id}/building-codes
# ---------------------------------------------------------------------------


class TestAddBuildingCode:
    async def test_add_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/building-codes",
            json={"wa_code_id": wac.id, "school_id": school.id, "budget": "10000.00"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["wa_code_id"] == wac.id
        assert data["school_id"] == school.id
        assert data["budget"] == "10000.00"

    async def test_project_level_code_rejected(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="P-001", level=WACodeLevel.PROJECT)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/building-codes",
            json={"wa_code_id": wac.id, "school_id": school.id, "budget": "10000.00"},
        )
        assert response.status_code == 422

    async def test_school_not_on_project_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session, code="K001")
        other_school = await _seed_school(db_session, code="K002")
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/building-codes",
            json={"wa_code_id": wac.id, "school_id": other_school.id, "budget": "5000.00"},
        )
        assert response.status_code == 422

    async def test_duplicate_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)

        await auth_client.post(
            f"/work-auths/{wa.id}/building-codes",
            json={"wa_code_id": wac.id, "school_id": school.id, "budget": "10000.00"},
        )
        response = await auth_client.post(
            f"/work-auths/{wa.id}/building-codes",
            json={"wa_code_id": wac.id, "school_id": school.id, "budget": "10000.00"},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# GET /work-auths/{id}/building-codes
# ---------------------------------------------------------------------------


class TestListBuildingCodes:
    async def test_list_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)
        db_session.add(WorkAuthBuildingCode(
            work_auth_id=wa.id, wa_code_id=wac.id,
            project_id=project.id, school_id=school.id,
            budget="5000.00", status=WACodeStatus.ACTIVE,
        ))
        await db_session.flush()

        response = await auth_client.get(f"/work-auths/{wa.id}/building-codes")
        assert response.status_code == 200
        assert len(response.json()) == 1


# ---------------------------------------------------------------------------
# PATCH /work-auths/{id}/building-codes/{wa_code_id}/{school_id}
# ---------------------------------------------------------------------------


class TestUpdateBuildingCode:
    async def test_update_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)
        db_session.add(WorkAuthBuildingCode(
            work_auth_id=wa.id, wa_code_id=wac.id,
            project_id=project.id, school_id=school.id,
            budget="5000.00", status=WACodeStatus.RFA_NEEDED,
        ))
        await db_session.flush()

        response = await auth_client.patch(
            f"/work-auths/{wa.id}/building-codes/{wac.id}/{school.id}",
            json={"budget": "7500.00", "status": "active"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["budget"] == "7500.00"
        assert data["status"] == WACodeStatus.ACTIVE


# ---------------------------------------------------------------------------
# DELETE /work-auths/{id}/building-codes/{wa_code_id}/{school_id}
# ---------------------------------------------------------------------------


class TestDeleteBuildingCode:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)
        db_session.add(WorkAuthBuildingCode(
            work_auth_id=wa.id, wa_code_id=wac.id,
            project_id=project.id, school_id=school.id,
            budget="5000.00", status=WACodeStatus.ACTIVE,
        ))
        await db_session.flush()

        response = await auth_client.delete(
            f"/work-auths/{wa.id}/building-codes/{wac.id}/{school.id}"
        )
        assert response.status_code == 204

        follow_up = await auth_client.get(f"/work-auths/{wa.id}/building-codes")
        assert follow_up.json() == []

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/work-auths/9999/building-codes/1/1")
        assert response.status_code == 404
