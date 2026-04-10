"""
Integration tests for RFA endpoints.

POST   /work-auths/{wa_id}/rfas             — create RFA
GET    /work-auths/{wa_id}/rfas             — list RFA history
PATCH  /work-auths/{wa_id}/rfas/{rfa_id}   — resolve RFA
"""

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro, RFAAction, RFAStatus, WACodeLevel, WACodeStatus
from app.projects.models import Project
from app.schools.models import School
from app.wa_codes.models import WACode
from app.work_auths.models import (
    RFA,
    WorkAuth,
    WorkAuthBuildingCode,
    WorkAuthProjectCode,
)

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


async def _seed_wa_code(
    db: AsyncSession,
    code: str = "P-001",
    level: WACodeLevel = WACodeLevel.PROJECT,
) -> WACode:
    wac = WACode(code=code, description=f"Description for {code}", level=level)
    db.add(wac)
    await db.flush()
    return wac


async def _seed_project_code(
    db: AsyncSession,
    wa: WorkAuth,
    wac: WACode,
    status: WACodeStatus = WACodeStatus.RFA_NEEDED,
    fee: str = "500.00",
) -> WorkAuthProjectCode:
    wapc = WorkAuthProjectCode(
        work_auth_id=wa.id,
        wa_code_id=wac.id,
        fee=fee,
        status=status,
    )
    db.add(wapc)
    await db.flush()
    return wapc


async def _seed_building_code(
    db: AsyncSession,
    wa: WorkAuth,
    wac: WACode,
    project: Project,
    school: School,
    status: WACodeStatus = WACodeStatus.RFA_NEEDED,
    budget: str = "10000.00",
) -> WorkAuthBuildingCode:
    wabc = WorkAuthBuildingCode(
        work_auth_id=wa.id,
        wa_code_id=wac.id,
        project_id=project.id,
        school_id=school.id,
        budget=budget,
        status=status,
    )
    db.add(wabc)
    await db.flush()
    return wabc


async def _seed_rfa(
    db: AsyncSession,
    wa: WorkAuth,
    status: RFAStatus = RFAStatus.PENDING,
    notes: str | None = None,
) -> RFA:
    rfa = RFA(work_auth_id=wa.id, status=status, notes=notes)
    db.add(rfa)
    await db.flush()
    return rfa


# ---------------------------------------------------------------------------
# POST /work-auths/{wa_id}/rfas
# ---------------------------------------------------------------------------


class TestCreateRFA:
    async def test_create_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/rfas",
            json={"notes": "Initial submission"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["work_auth_id"] == wa.id
        assert data["status"] == RFAStatus.PENDING
        assert data["notes"] == "Initial submission"
        assert data["resolved_at"] is None

    async def test_create_with_project_codes(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/rfas",
            json={"project_codes": [{"wa_code_id": wac.id, "action": "add"}]},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["project_codes"]) == 1
        assert data["project_codes"][0]["action"] == RFAAction.ADD

    async def test_create_with_building_codes(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/rfas",
            json={
                "building_codes": [
                    {
                        "wa_code_id": wac.id,
                        "school_id": school.id,
                        "action": "add",
                        "budget_adjustment": "2500.00",
                    }
                ]
            },
        )
        assert response.status_code == 201
        bc = response.json()["building_codes"][0]
        assert bc["action"] == RFAAction.ADD
        assert bc["budget_adjustment"] == "2500.00"

    async def test_create_marks_project_code_rfa_pending(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)
        wapc = await _seed_project_code(db_session, wa, wac, status=WACodeStatus.RFA_NEEDED)

        await auth_client.post(
            f"/work-auths/{wa.id}/rfas",
            json={"project_codes": [{"wa_code_id": wac.id, "action": "add"}]},
        )

        await db_session.refresh(wapc)
        assert wapc.status == WACodeStatus.RFA_PENDING

    async def test_create_marks_building_code_rfa_pending(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)
        wabc = await _seed_building_code(db_session, wa, wac, project, school)

        await auth_client.post(
            f"/work-auths/{wa.id}/rfas",
            json={
                "building_codes": [
                    {"wa_code_id": wac.id, "school_id": school.id, "action": "add"}
                ]
            },
        )

        await db_session.refresh(wabc)
        assert wabc.status == WACodeStatus.RFA_PENDING

    async def test_second_pending_rfa_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        await _seed_rfa(db_session, wa, status=RFAStatus.PENDING)

        response = await auth_client.post(
            f"/work-auths/{wa.id}/rfas",
            json={},
        )
        assert response.status_code == 409

    async def test_can_create_after_resolved_rfa(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """A resolved RFA does not block a new one."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        await _seed_rfa(db_session, wa, status=RFAStatus.APPROVED)

        response = await auth_client.post(f"/work-auths/{wa.id}/rfas", json={})
        assert response.status_code == 201

    async def test_missing_wa_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post("/work-auths/9999/rfas", json={})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /work-auths/{wa_id}/rfas
# ---------------------------------------------------------------------------


class TestListRFAs:
    async def test_list_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        await _seed_rfa(db_session, wa, status=RFAStatus.APPROVED)
        await _seed_rfa(db_session, wa, status=RFAStatus.PENDING)

        response = await auth_client.get(f"/work-auths/{wa.id}/rfas")
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_list_empty(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)

        response = await auth_client.get(f"/work-auths/{wa.id}/rfas")
        assert response.status_code == 200
        assert response.json() == []

    async def test_missing_wa_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/work-auths/9999/rfas")
        assert response.status_code == 404

    async def test_only_returns_rfas_for_that_wa(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project_a = await _seed_project(db_session, school, number="26-111-01")
        project_b = await _seed_project(db_session, school, number="26-111-02")
        wa_a = await _seed_work_auth(
            db_session, project_a, wa_num="WA-001", service_id="SVC-001", project_num="PN-001"
        )
        wa_b = await _seed_work_auth(
            db_session, project_b, wa_num="WA-002", service_id="SVC-002", project_num="PN-002"
        )
        await _seed_rfa(db_session, wa_a)
        await _seed_rfa(db_session, wa_b)

        response = await auth_client.get(f"/work-auths/{wa_a.id}/rfas")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["work_auth_id"] == wa_a.id


# ---------------------------------------------------------------------------
# PATCH /work-auths/{wa_id}/rfas/{rfa_id}
# ---------------------------------------------------------------------------


class TestResolveRFA:
    async def test_approve_sets_resolved_at(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        rfa = await _seed_rfa(db_session, wa)

        response = await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "approved"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == RFAStatus.APPROVED
        assert data["resolved_at"] is not None

    async def test_approve_add_sets_project_code_added_by_rfa(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)
        wapc = await _seed_project_code(db_session, wa, wac, status=WACodeStatus.RFA_PENDING)
        rfa = await _seed_rfa(db_session, wa)
        from app.work_auths.models import RFAProjectCode
        db_session.add(RFAProjectCode(rfa_id=rfa.id, wa_code_id=wac.id, action=RFAAction.ADD))
        await db_session.flush()

        await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "approved"},
        )

        await db_session.refresh(wapc)
        assert wapc.status == WACodeStatus.ADDED_BY_RFA

    async def test_approve_remove_sets_project_code_removed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)
        wapc = await _seed_project_code(db_session, wa, wac, status=WACodeStatus.RFA_PENDING)
        rfa = await _seed_rfa(db_session, wa)
        from app.work_auths.models import RFAProjectCode
        db_session.add(RFAProjectCode(rfa_id=rfa.id, wa_code_id=wac.id, action=RFAAction.REMOVE))
        await db_session.flush()

        await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "approved"},
        )

        await db_session.refresh(wapc)
        assert wapc.status == WACodeStatus.REMOVED

    async def test_approve_add_sets_building_code_added_by_rfa(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)
        wabc = await _seed_building_code(
            db_session, wa, wac, project, school, status=WACodeStatus.RFA_PENDING
        )
        rfa = await _seed_rfa(db_session, wa)
        from app.work_auths.models import RFABuildingCode
        db_session.add(RFABuildingCode(
            rfa_id=rfa.id,
            wa_code_id=wac.id,
            project_id=project.id,
            school_id=school.id,
            action=RFAAction.ADD,
        ))
        await db_session.flush()

        await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "approved"},
        )

        await db_session.refresh(wabc)
        assert wabc.status == WACodeStatus.ADDED_BY_RFA

    async def test_approve_applies_budget_adjustment(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)
        wabc = await _seed_building_code(
            db_session, wa, wac, project, school, budget="10000.00"
        )
        rfa = await _seed_rfa(db_session, wa)
        from app.work_auths.models import RFABuildingCode
        db_session.add(RFABuildingCode(
            rfa_id=rfa.id,
            wa_code_id=wac.id,
            project_id=project.id,
            school_id=school.id,
            action=RFAAction.ADD,
            budget_adjustment="2500.00",
        ))
        await db_session.flush()

        await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "approved"},
        )

        await db_session.refresh(wabc)
        assert wabc.budget == 12500

    async def test_reject_reverts_project_code_to_rfa_needed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)
        wapc = await _seed_project_code(db_session, wa, wac, status=WACodeStatus.RFA_PENDING)
        rfa = await _seed_rfa(db_session, wa)
        from app.work_auths.models import RFAProjectCode
        db_session.add(RFAProjectCode(rfa_id=rfa.id, wa_code_id=wac.id, action=RFAAction.ADD))
        await db_session.flush()

        await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "rejected"},
        )

        await db_session.refresh(wapc)
        assert wapc.status == WACodeStatus.RFA_NEEDED

    async def test_reject_reverts_building_code_to_rfa_needed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, code="B-001", level=WACodeLevel.BUILDING)
        wabc = await _seed_building_code(
            db_session, wa, wac, project, school, status=WACodeStatus.RFA_PENDING
        )
        rfa = await _seed_rfa(db_session, wa)
        from app.work_auths.models import RFABuildingCode
        db_session.add(RFABuildingCode(
            rfa_id=rfa.id,
            wa_code_id=wac.id,
            project_id=project.id,
            school_id=school.id,
            action=RFAAction.ADD,
        ))
        await db_session.flush()

        await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "rejected"},
        )

        await db_session.refresh(wabc)
        assert wabc.status == WACodeStatus.RFA_NEEDED

    async def test_withdraw_reverts_codes_to_rfa_needed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        wac = await _seed_wa_code(db_session, level=WACodeLevel.PROJECT)
        wapc = await _seed_project_code(db_session, wa, wac, status=WACodeStatus.RFA_PENDING)
        rfa = await _seed_rfa(db_session, wa)
        from app.work_auths.models import RFAProjectCode
        db_session.add(RFAProjectCode(rfa_id=rfa.id, wa_code_id=wac.id, action=RFAAction.ADD))
        await db_session.flush()

        await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "withdrawn"},
        )

        await db_session.refresh(wapc)
        assert wapc.status == WACodeStatus.RFA_NEEDED

    async def test_notes_updated_on_resolve(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        rfa = await _seed_rfa(db_session, wa, notes="original notes")

        response = await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "rejected", "notes": "rejected by coordinator"},
        )
        assert response.json()["notes"] == "rejected by coordinator"

    async def test_resolve_already_resolved_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        rfa = await _seed_rfa(db_session, wa, status=RFAStatus.APPROVED)

        response = await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "rejected"},
        )
        assert response.status_code == 409

    async def test_resolve_to_pending_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)
        rfa = await _seed_rfa(db_session, wa)

        response = await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa.id}",
            json={"status": "pending"},
        )
        assert response.status_code == 422

    async def test_missing_rfa_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa = await _seed_work_auth(db_session, project)

        response = await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/9999",
            json={"status": "approved"},
        )
        assert response.status_code == 404

    async def test_missing_wa_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            "/work-auths/9999/rfas/1",
            json={"status": "approved"},
        )
        assert response.status_code == 404
