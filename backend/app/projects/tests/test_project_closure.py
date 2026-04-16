"""
Endpoint tests for POST /projects/{id}/close and locked-record guards.
"""

from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import (
    Boro,
    EmployeeRoleType,
    NoteEntityType,
    ProjectStatus,
    SampleBatchStatus,
    TimeEntryStatus,
)
from app.employees.models import Employee, EmployeeRole
from app.lab_results.models import SampleBatch, SampleType
from app.notes.models import Note
from app.projects.models import Project
from app.schools.models import School
from app.time_entries.models import TimeEntry


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


async def _seed_school(db: AsyncSession) -> School:
    school = School(
        code="K300",
        name="Closure Test School",
        address="300 Test St",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()
    return school


async def _seed_project(db: AsyncSession, school: School) -> Project:
    project = Project(name="Closure Test Project", project_number="26-222-99")
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


async def _seed_employee_with_role(db: AsyncSession) -> tuple[Employee, EmployeeRole]:
    emp = Employee(first_name="Close", last_name="Tester")
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


async def _seed_time_entry(
    db: AsyncSession,
    project: Project,
    school: School,
    emp: Employee,
    role: EmployeeRole,
    *,
    status: TimeEntryStatus = TimeEntryStatus.ENTERED,
) -> TimeEntry:
    entry = TimeEntry(
        start_datetime=datetime(2025, 6, 1, 9, 0, 0),
        end_datetime=datetime(2025, 6, 1, 17, 0, 0),
        employee_id=emp.id,
        employee_role_id=role.id,
        project_id=project.id,
        school_id=school.id,
        status=status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(entry)
    await db.flush()
    return entry


async def _seed_sample_type(db: AsyncSession) -> SampleType:
    st = SampleType(
        name="PCM-Close", created_by_id=SYSTEM_USER_ID, updated_by_id=SYSTEM_USER_ID
    )
    db.add(st)
    await db.flush()
    return st


async def _seed_batch(
    db: AsyncSession,
    time_entry: TimeEntry,
    sample_type: SampleType,
    *,
    status: SampleBatchStatus = SampleBatchStatus.ACTIVE,
) -> SampleBatch:
    batch = SampleBatch(
        sample_type_id=sample_type.id,
        time_entry_id=time_entry.id,
        batch_num=f"CLOSE-BATCH-{time_entry.id}",
        is_report=False,
        date_collected=date(2025, 6, 1),
        status=status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(batch)
    await db.flush()
    return batch


async def _seed_blocking_note(
    db: AsyncSession, entity_type: NoteEntityType, entity_id: int
) -> Note:
    note = Note(
        entity_type=entity_type,
        entity_id=entity_id,
        body="Blocking issue for closure test",
        is_blocking=True,
        is_resolved=False,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(note)
    await db.flush()
    return note


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
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        await _seed_time_entry(db_session, project, school, emp, role)
        await _seed_blocking_note(db_session, NoteEntityType.PROJECT, project.id)

        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 409
        body = response.json()
        assert "blocking_issues" in body["detail"]
        assert len(body["detail"]["blocking_issues"]) == 1

    async def test_close_succeeds_and_returns_locked_status(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        await _seed_time_entry(db_session, project, school, emp, role)

        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 200
        assert response.json()["status"] == ProjectStatus.LOCKED

    async def test_close_locks_time_entries(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await _seed_time_entry(
            db_session, project, school, emp, role, status=TimeEntryStatus.ASSUMED
        )

        await auth_client.post(f"/projects/{project.id}/close")

        await db_session.refresh(entry)
        assert entry.status == TimeEntryStatus.LOCKED

    async def test_close_locks_active_batches(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await _seed_time_entry(db_session, project, school, emp, role)
        st = await _seed_sample_type(db_session)
        batch = await _seed_batch(db_session, entry, st)

        await auth_client.post(f"/projects/{project.id}/close")

        await db_session.refresh(batch)
        assert batch.status == SampleBatchStatus.LOCKED

    async def test_close_does_not_change_discarded_batches(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await _seed_time_entry(db_session, project, school, emp, role)
        st = await _seed_sample_type(db_session)
        batch = await _seed_batch(
            db_session, entry, st, status=SampleBatchStatus.DISCARDED
        )

        await auth_client.post(f"/projects/{project.id}/close")

        await db_session.refresh(batch)
        assert batch.status == SampleBatchStatus.DISCARDED

    async def test_409_when_already_closed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        await auth_client.post(f"/projects/{project.id}/close")
        response = await auth_client.post(f"/projects/{project.id}/close")

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Tests: locked record guards
# ---------------------------------------------------------------------------


class TestLockedTimeEntryGuards:
    async def test_patch_locked_time_entry_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await _seed_time_entry(
            db_session, project, school, emp, role, status=TimeEntryStatus.LOCKED
        )

        response = await auth_client.patch(
            f"/time-entries/{entry.id}", json={"notes": "updated"}
        )
        assert response.status_code == 422

    async def test_delete_locked_time_entry_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await _seed_time_entry(
            db_session, project, school, emp, role, status=TimeEntryStatus.LOCKED
        )

        response = await auth_client.delete(f"/time-entries/{entry.id}")
        assert response.status_code == 422


class TestLockedBatchGuards:
    async def test_patch_locked_batch_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await _seed_time_entry(db_session, project, school, emp, role)
        st = await _seed_sample_type(db_session)
        batch = await _seed_batch(
            db_session, entry, st, status=SampleBatchStatus.LOCKED
        )

        response = await auth_client.patch(
            f"/lab-results/batches/{batch.id}", json={"notes": "updated"}
        )
        assert response.status_code == 422

    async def test_delete_locked_batch_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        emp, role = await _seed_employee_with_role(db_session)
        entry = await _seed_time_entry(db_session, project, school, emp, role)
        st = await _seed_sample_type(db_session)
        batch = await _seed_batch(
            db_session, entry, st, status=SampleBatchStatus.LOCKED
        )

        response = await auth_client.delete(f"/lab-results/batches/{batch.id}")
        assert response.status_code == 422
