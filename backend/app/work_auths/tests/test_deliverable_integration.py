"""
Integration tests verifying that WA code and RFA mutations automatically
keep deliverable SCA statuses and deliverable rows up to date.

These tests exercise the wiring added in Phase 6 Session B.
"""

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import (
    Boro,
    RFAAction,
    RFAStatus,
    SCADeliverableStatus,
    WACodeLevel,
    WACodeStatus,
)
from app.deliverables.models import (
    Deliverable,
    DeliverableWACodeTrigger,
    ProjectDeliverable,
)
from app.projects.models import Project
from app.schools.models import School
from app.wa_codes.models import WACode
from app.work_auths.models import WorkAuth, WorkAuthProjectCode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_school(db: AsyncSession) -> School:
    school = School(
        code="K901",
        name="Integration School",
        address="1 Test Ave",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()
    return school


async def _seed_project(db: AsyncSession, school: School) -> Project:
    project = Project(name="Integration Project", project_number="26-901-0001")
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


async def _seed_wa_code(
    db: AsyncSession, code: str, level: WACodeLevel = WACodeLevel.PROJECT
) -> WACode:
    wac = WACode(
        code=code,
        description=f"Desc {code}",
        level=level,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(wac)
    await db.flush()
    return wac


async def _seed_deliverable_with_trigger(
    db: AsyncSession, name: str, wa_code: WACode
) -> Deliverable:
    deliv = Deliverable(
        name=name,
        level=WACodeLevel.PROJECT,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(deliv)
    await db.flush()
    trigger = DeliverableWACodeTrigger(
        deliverable_id=deliv.id,
        wa_code_id=wa_code.id,
    )
    db.add(trigger)
    await db.flush()
    return deliv


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeliverableIntegration:
    async def test_add_project_code_creates_and_sets_deliverable_outstanding(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """POST /work-auths/{id}/project-codes creates the deliverable row and sets
        sca_status=OUTSTANDING when the added code is ACTIVE."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa_code = await _seed_wa_code(db_session, "P-INT-01")
        deliv = await _seed_deliverable_with_trigger(db_session, "Integration Deliv 1", wa_code)

        # Create WA via API (also triggers ensure + recalculate but no codes yet)
        wa_resp = await auth_client.post(
            "/work-auths",
            json={
                "wa_num": "WA-INT-01",
                "service_id": "SVC-INT-01",
                "project_num": "PN-INT-01",
                "initiation_date": "2025-01-01",
                "project_id": project.id,
            },
        )
        assert wa_resp.status_code == 201
        wa_id = wa_resp.json()["id"]

        # Add a project code — deliverable should be created and set OUTSTANDING
        code_resp = await auth_client.post(
            f"/work-auths/{wa_id}/project-codes",
            json={"wa_code_id": wa_code.id, "fee": "500.00", "status": "active"},
        )
        assert code_resp.status_code == 201

        pd = (
            await db_session.execute(
                select(ProjectDeliverable).where(
                    ProjectDeliverable.project_id == project.id,
                    ProjectDeliverable.deliverable_id == deliv.id,
                )
            )
        ).scalar_one()
        assert pd.sca_status == SCADeliverableStatus.OUTSTANDING

    async def test_delete_project_code_reverts_deliverable_to_pending_wa(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """DELETE /work-auths/{id}/project-codes/{code_id} recalculates status;
        removing the only code reverts deliverable to PENDING_WA."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa_code = await _seed_wa_code(db_session, "P-INT-02")
        deliv = await _seed_deliverable_with_trigger(db_session, "Integration Deliv 2", wa_code)

        wa = WorkAuth(
            wa_num="WA-INT-02",
            service_id="SVC-INT-02",
            project_num="PN-INT-02",
            initiation_date=date(2025, 1, 1),
            project_id=project.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(wa)
        await db_session.flush()

        # Add active project code and deliverable row directly
        pc = WorkAuthProjectCode(
            work_auth_id=wa.id,
            wa_code_id=wa_code.id,
            fee=Decimal("100.00"),
            status=WACodeStatus.ACTIVE,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(pc)
        pd_row = ProjectDeliverable(
            project_id=project.id,
            deliverable_id=deliv.id,
            sca_status=SCADeliverableStatus.OUTSTANDING,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(pd_row)
        await db_session.flush()

        del_resp = await auth_client.delete(
            f"/work-auths/{wa.id}/project-codes/{wa_code.id}"
        )
        assert del_resp.status_code == 204

        await db_session.refresh(pd_row)
        assert pd_row.sca_status == SCADeliverableStatus.PENDING_WA

    async def test_rfa_approved_advances_deliverable_to_outstanding(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """PATCH /work-auths/{id}/rfas/{id} with approved status advances a
        PENDING_RFA deliverable to OUTSTANDING when the code becomes ADDED_BY_RFA."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa_code = await _seed_wa_code(db_session, "P-INT-03")
        deliv = await _seed_deliverable_with_trigger(db_session, "Integration Deliv 3", wa_code)

        wa = WorkAuth(
            wa_num="WA-INT-03",
            service_id="SVC-INT-03",
            project_num="PN-INT-03",
            initiation_date=date(2025, 1, 1),
            project_id=project.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(wa)
        await db_session.flush()

        pc = WorkAuthProjectCode(
            work_auth_id=wa.id,
            wa_code_id=wa_code.id,
            fee=Decimal("100.00"),
            status=WACodeStatus.RFA_NEEDED,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(pc)
        pd_row = ProjectDeliverable(
            project_id=project.id,
            deliverable_id=deliv.id,
            sca_status=SCADeliverableStatus.PENDING_RFA,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(pd_row)
        await db_session.flush()

        # Create RFA
        rfa_resp = await auth_client.post(
            f"/work-auths/{wa.id}/rfas",
            json={
                "submitted_by_id": None,
                "notes": None,
                "project_codes": [{"wa_code_id": wa_code.id, "action": "add"}],
                "building_codes": [],
            },
        )
        assert rfa_resp.status_code == 201
        rfa_id = rfa_resp.json()["id"]

        # Approve RFA
        approve_resp = await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa_id}",
            json={"status": "approved", "notes": None},
        )
        assert approve_resp.status_code == 200

        await db_session.refresh(pd_row)
        assert pd_row.sca_status == SCADeliverableStatus.OUTSTANDING

    async def test_rfa_rejected_keeps_deliverable_at_pending_rfa(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """PATCH /work-auths/{id}/rfas/{id} with rejected status leaves deliverable
        at PENDING_RFA (code reverts to RFA_NEEDED)."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        wa_code = await _seed_wa_code(db_session, "P-INT-04")
        deliv = await _seed_deliverable_with_trigger(db_session, "Integration Deliv 4", wa_code)

        wa = WorkAuth(
            wa_num="WA-INT-04",
            service_id="SVC-INT-04",
            project_num="PN-INT-04",
            initiation_date=date(2025, 1, 1),
            project_id=project.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(wa)
        await db_session.flush()

        pc = WorkAuthProjectCode(
            work_auth_id=wa.id,
            wa_code_id=wa_code.id,
            fee=Decimal("100.00"),
            status=WACodeStatus.RFA_NEEDED,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(pc)
        pd_row = ProjectDeliverable(
            project_id=project.id,
            deliverable_id=deliv.id,
            sca_status=SCADeliverableStatus.PENDING_RFA,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(pd_row)
        await db_session.flush()

        rfa_resp = await auth_client.post(
            f"/work-auths/{wa.id}/rfas",
            json={
                "submitted_by_id": None,
                "notes": None,
                "project_codes": [{"wa_code_id": wa_code.id, "action": "add"}],
                "building_codes": [],
            },
        )
        assert rfa_resp.status_code == 201
        rfa_id = rfa_resp.json()["id"]

        reject_resp = await auth_client.patch(
            f"/work-auths/{wa.id}/rfas/{rfa_id}",
            json={"status": "rejected", "notes": None},
        )
        assert reject_resp.status_code == 200

        await db_session.refresh(pd_row)
        assert pd_row.sca_status == SCADeliverableStatus.PENDING_RFA
