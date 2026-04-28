"""
Endpoint tests for POST /projects/{id}/close and locked-record guards.
"""

from datetime import date, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import (
    EmployeeRoleType,
    NoteEntityType,
    ProjectStatus,
    SampleBatchStatus,
    TimeEntryStatus,
)
from app.employees.models import Employee, EmployeeRole
from app.notes.models import Note
from tests.seeds import (
    seed_blocking_note,
    seed_contractor,
    seed_project,
    seed_sample_batch,
    seed_sample_type,
    seed_school,
    seed_time_entry,
)

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


async def _seed_employee_with_role(db: AsyncSession) -> tuple[Employee, EmployeeRole]:
    emp = Employee(first_name="Close", last_name="Tester", display_name="Close Tester")
    db.add(emp)
    await db.flush()
    role = EmployeeRole(
        employee_id=emp.id,
        role_type=EmployeeRoleType.ACM_PROJECT_MONITOR,
        start_date=date(2025, 1, 1),
        hourly_rate="75.00",
    )
    db.add(role)
    await db.flush()
    return emp, role


# ---------------------------------------------------------------------------
# Tests: POST /projects/{id}/close
# ---------------------------------------------------------------------------


class TestCloseProject:
    async def test_404_for_unknown_project(self, auth_client: AsyncClient):
        response = await auth_client.post("/projects/9999/close")
        assert response.status_code == 404

    async def test_409_when_blocking_notes_exist(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        await seed_time_entry(db_session, emp, role, project, school)
        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.PROJECT, entity_id=project.id
        )

        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 409
        body = response.json()
        assert "blocking_issues" in body["detail"]
        assert len(body["detail"]["blocking_issues"]) == 1

    async def test_close_succeeds_and_returns_locked_status(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 200
        assert response.json()["status"] == ProjectStatus.LOCKED

    async def test_close_locks_time_entries(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await seed_time_entry(
            db_session, emp, role, project, school, status=TimeEntryStatus.ASSUMED
        )

        await auth_client.post(f"/projects/{project.id}/close")

        await db_session.refresh(entry)
        assert entry.status == TimeEntryStatus.LOCKED

    async def test_close_locks_active_batches(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        st = await seed_sample_type(db_session)
        batch = await seed_sample_batch(db_session, entry, st)

        await auth_client.post(f"/projects/{project.id}/close")

        await db_session.refresh(batch)
        assert batch.status == SampleBatchStatus.LOCKED

    async def test_close_does_not_change_discarded_batches(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        st = await seed_sample_type(db_session)
        batch = await seed_sample_batch(
            db_session, entry, st, status=SampleBatchStatus.DISCARDED
        )

        await auth_client.post(f"/projects/{project.id}/close")

        await db_session.refresh(batch)
        assert batch.status == SampleBatchStatus.DISCARDED

    async def test_409_when_already_closed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        await auth_client.post(f"/projects/{project.id}/close")
        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 409

    async def test_409_when_unfulfilled_requirements_exist(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.cprs.models import ContractorPaymentRecord

        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        await seed_time_entry(db_session, emp, role, project, school)
        contractor = await seed_contractor(db_session)
        db_session.add(
            ContractorPaymentRecord(project_id=project.id, contractor_id=contractor.id)
        )
        await db_session.flush()

        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 409
        body = response.json()
        assert "unfulfilled_requirements" in body["detail"]
        assert len(body["detail"]["unfulfilled_requirements"]) == 1

    async def test_409_blocking_notes_takes_precedence_over_unfulfilled(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """Blocking notes raise first; unfulfilled requirements are not checked."""
        from app.cprs.models import ContractorPaymentRecord

        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        await seed_time_entry(db_session, emp, role, project, school)
        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.PROJECT, entity_id=project.id
        )
        contractor = await seed_contractor(db_session)
        db_session.add(
            ContractorPaymentRecord(project_id=project.id, contractor_id=contractor.id)
        )
        await db_session.flush()

        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 409
        body = response.json()
        assert "blocking_issues" in body["detail"]

    async def test_close_succeeds_when_requirements_fulfilled(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from datetime import datetime

        from app.cprs.models import ContractorPaymentRecord

        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        await seed_time_entry(db_session, emp, role, project, school)
        contractor = await seed_contractor(db_session)
        db_session.add(
            ContractorPaymentRecord(
                project_id=project.id,
                contractor_id=contractor.id,
                rfp_saved_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 200
        assert response.json()["status"] == ProjectStatus.LOCKED


# ---------------------------------------------------------------------------
# Tests: locked record guards
# ---------------------------------------------------------------------------


class TestLockedTimeEntryGuards:
    async def test_patch_locked_time_entry_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await seed_time_entry(
            db_session, emp, role, project, school, status=TimeEntryStatus.LOCKED
        )

        response = await auth_client.patch(
            f"/time-entries/{entry.id}", json={"notes": "updated"}
        )
        assert response.status_code == 422

    async def test_delete_locked_time_entry_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await seed_time_entry(
            db_session, emp, role, project, school, status=TimeEntryStatus.LOCKED
        )

        response = await auth_client.delete(f"/time-entries/{entry.id}")
        assert response.status_code == 422


class TestLockedBatchGuards:
    async def test_patch_locked_batch_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        st = await seed_sample_type(db_session)
        batch = await seed_sample_batch(
            db_session, entry, st, status=SampleBatchStatus.LOCKED
        )

        response = await auth_client.patch(
            f"/lab-results/batches/{batch.id}", json={"notes": "updated"}
        )
        assert response.status_code == 422

    async def test_delete_locked_batch_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        st = await seed_sample_type(db_session)
        batch = await seed_sample_batch(
            db_session, entry, st, status=SampleBatchStatus.LOCKED
        )

        response = await auth_client.delete(f"/lab-results/batches/{batch.id}")
        assert response.status_code == 422
