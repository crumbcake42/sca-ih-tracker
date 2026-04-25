"""
Integration tests for time entry endpoints.

POST   /time-entries/
PATCH  /time-entries/{id}
GET    /time-entries/
GET    /time-entries/{id}
DELETE /time-entries/{id}
"""

from datetime import date, datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import SampleBatchStatus, TimeEntryStatus
from app.lab_results.models import SampleBatch, SampleType
from app.time_entries.models import TimeEntry

from tests.seeds import (
    DT_START,
    DT_END,
    seed_school,
    seed_project,
    seed_employee,
    seed_employee_role,
    seed_time_entry,
)

# ---------------------------------------------------------------------------
# POST /time-entries/
# ---------------------------------------------------------------------------


class TestCreateTimeEntry:
    async def test_create_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "end_datetime": DT_END.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["employee_id"] == emp.id
        assert data["employee_role_id"] == role.id
        assert data["project_id"] == project.id
        assert data["school_id"] == school.id
        assert data["end_datetime"] is not None

    async def test_create_without_end_time(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 201
        assert response.json()["end_datetime"] is None

    async def test_missing_employee_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "employee_id": 9999,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 404

    async def test_missing_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": 9999,
                "school_id": school.id,
            },
        )
        assert response.status_code == 404

    async def test_school_not_on_project_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        other_school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": other_school.id,
            },
        )
        assert response.status_code == 422

    async def test_role_not_belonging_to_employee_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp1 = await seed_employee(db_session)
        emp2 = await seed_employee(db_session)
        role_for_emp2 = await seed_employee_role(db_session, emp2)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "employee_id": emp1.id,
                "employee_role_id": role_for_emp2.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 422

    async def test_role_not_yet_active_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        # Role starts 2026-01-01, entry is Nov 2025
        role = await seed_employee_role(db_session, emp, start=date(2026, 1, 1))

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 422

    async def test_role_expired_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        # Role ended 2025-06-30, entry is Nov 2025
        role = await seed_employee_role(db_session, emp, end=date(2025, 6, 30))

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 422

    async def test_end_before_start_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_END.isoformat(),
                "end_datetime": DT_START.isoformat(),  # reversed
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /time-entries/ and /time-entries/{id}
# ---------------------------------------------------------------------------


class TestGetTimeEntries:
    async def test_list_all_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.get("/time-entries/")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    async def test_filter_by_project_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.get(f"/time-entries/?project_id={project.id}")
        assert response.status_code == 200
        data = response.json()
        assert all(e["project_id"] == project.id for e in data)

    async def test_get_by_id_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.get(f"/time-entries/{entry.id}")
        assert response.status_code == 200
        assert response.json()["id"] == entry.id

    async def test_get_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/time-entries/9999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /time-entries/{id}
# ---------------------------------------------------------------------------


class TestUpdateTimeEntry:
    async def test_add_end_time_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        # Create entry without end time
        entry = TimeEntry(
            start_datetime=DT_START,
            employee_id=emp.id,
            employee_role_id=role.id,
            project_id=project.id,
            school_id=school.id,
        )
        db_session.add(entry)
        await db_session.flush()

        response = await auth_client.patch(
            f"/time-entries/{entry.id}",
            json={"end_datetime": DT_END.isoformat()},
        )
        assert response.status_code == 200
        assert response.json()["end_datetime"] is not None

    async def test_update_notes(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.patch(
            f"/time-entries/{entry.id}",
            json={"notes": "Adjusted per field log"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Adjusted per field log"

    async def test_update_start_datetime_revalidates_role(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        # Role started 2025-01-01
        role = await seed_employee_role(db_session, emp, start=date(2025, 1, 1))
        entry = await seed_time_entry(db_session, emp, role, project, school)

        # Move start_datetime to 2024 — role wasn't active yet
        bad_start = datetime(2024, 6, 1, 9, 0, 0)
        response = await auth_client.patch(
            f"/time-entries/{entry.id}",
            json={"start_datetime": bad_start.isoformat()},
        )
        assert response.status_code == 422

    async def test_end_before_existing_start_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        # DT_START is 5 PM; try to set end to 4 PM same day
        before_start = datetime(2025, 11, 30, 16, 0, 0)
        response = await auth_client.patch(
            f"/time-entries/{entry.id}",
            json={"end_datetime": before_start.isoformat()},
        )
        assert response.status_code == 422

    async def test_patch_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            "/time-entries/9999",
            json={"notes": "whatever"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /time-entries/{id}
# ---------------------------------------------------------------------------


class TestDeleteTimeEntry:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.delete(f"/time-entries/{entry.id}")
        assert response.status_code == 204

        follow_up = await auth_client.get(f"/time-entries/{entry.id}")
        assert follow_up.status_code == 404

    async def test_delete_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/time-entries/9999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Audit field wiring
# ---------------------------------------------------------------------------


class TestAuditFields:
    async def test_create_sets_created_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 201
        entry = await db_session.get(TimeEntry, response.json()["id"])
        assert (
            entry and entry.created_by_id == 1
        )  # fake_user.id from auth_client fixture

    async def test_update_sets_updated_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.patch(
            f"/time-entries/{entry.id}",
            json={"notes": "audit test"},
        )
        assert response.status_code == 200
        await db_session.refresh(entry)
        assert entry.updated_by_id == 1  # fake_user.id from auth_client fixture


# ---------------------------------------------------------------------------
# Status field
# ---------------------------------------------------------------------------


class TestTimeEntryStatus:
    async def test_post_creates_entered_status(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "end_datetime": DT_END.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "entered"

    async def test_patch_assumed_entry_flips_to_entered(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        # Create an assumed entry directly (simulating quick-add output)
        entry = TimeEntry(
            start_datetime=DT_START,
            end_datetime=DT_END,
            employee_id=emp.id,
            employee_role_id=role.id,
            project_id=project.id,
            school_id=school.id,
            status=TimeEntryStatus.ASSUMED,
        )
        db_session.add(entry)
        await db_session.flush()

        response = await auth_client.patch(
            f"/time-entries/{entry.id}",
            json={"notes": "manager confirmed"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "entered"

    async def test_patch_entered_entry_stays_entered(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.patch(
            f"/time-entries/{entry.id}",
            json={"notes": "minor edit"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "entered"


# ---------------------------------------------------------------------------
# Overlap detection
# ---------------------------------------------------------------------------


class TestTimeEntryOverlap:
    async def test_post_overlap_same_employee_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        # Existing entry: 5PM–9PM
        await seed_time_entry(db_session, emp, role, project, school)

        # New entry: 6PM–10PM (overlaps)
        overlap_start = datetime(2025, 11, 30, 18, 0, 0)
        overlap_end = datetime(2025, 11, 30, 22, 0, 0)
        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": overlap_start.isoformat(),
                "end_datetime": overlap_end.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 422

    async def test_post_overlap_different_employee_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp1 = await seed_employee(db_session)
        emp2 = await seed_employee(db_session)
        role1 = await seed_employee_role(db_session, emp1)
        role2 = await seed_employee_role(db_session, emp2)

        # emp1 entry: 5PM–9PM
        await seed_time_entry(db_session, emp1, role1, project, school)

        # emp2 entry at same time: OK (different employee)
        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),
                "end_datetime": DT_END.isoformat(),
                "employee_id": emp2.id,
                "employee_role_id": role2.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 201

    async def test_post_back_to_back_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        # Existing entry ends at exactly DT_END (9PM)
        await seed_time_entry(db_session, emp, role, project, school)

        # New entry starts at exactly DT_END — no overlap (exclusive boundary)
        next_start = DT_END
        next_end = datetime(2025, 11, 30, 23, 0, 0)
        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": next_start.isoformat(),
                "end_datetime": next_end.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 201

    async def test_assumed_entry_blocks_same_day_post(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        # Assumed entry spans the full day (midnight Nov 30, no end time)
        midnight = datetime(2025, 11, 30, 0, 0, 0)
        entry = TimeEntry(
            start_datetime=midnight,
            end_datetime=None,
            employee_id=emp.id,
            employee_role_id=role.id,
            project_id=project.id,
            school_id=school.id,
            status=TimeEntryStatus.ASSUMED,
        )
        db_session.add(entry)
        await db_session.flush()

        # Any entry on Nov 30 should overlap
        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": DT_START.isoformat(),  # 5PM Nov 30
                "end_datetime": DT_END.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 422

    async def test_assumed_entry_does_not_block_next_day(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        # Assumed entry: midnight Nov 30, no end
        midnight = datetime(2025, 11, 30, 0, 0, 0)
        entry = TimeEntry(
            start_datetime=midnight,
            end_datetime=None,
            employee_id=emp.id,
            employee_role_id=role.id,
            project_id=project.id,
            school_id=school.id,
            status=TimeEntryStatus.ASSUMED,
        )
        db_session.add(entry)
        await db_session.flush()

        # Dec 1 entry should NOT overlap
        dec1 = datetime(2025, 12, 1, 9, 0, 0)
        dec1_end = datetime(2025, 12, 1, 17, 0, 0)
        response = await auth_client.post(
            "/time-entries/",
            json={
                "start_datetime": dec1.isoformat(),
                "end_datetime": dec1_end.isoformat(),
                "employee_id": emp.id,
                "employee_role_id": role.id,
                "project_id": project.id,
                "school_id": school.id,
            },
        )
        assert response.status_code == 201

    async def test_patch_into_overlap_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        # Entry 1: 5PM–9PM Nov 30
        await seed_time_entry(db_session, emp, role, project, school)

        # Entry 2: 10PM–11PM Nov 30 (no overlap yet)
        entry2 = TimeEntry(
            start_datetime=datetime(2025, 11, 30, 22, 0, 0),
            end_datetime=datetime(2025, 11, 30, 23, 0, 0),
            employee_id=emp.id,
            employee_role_id=role.id,
            project_id=project.id,
            school_id=school.id,
        )
        db_session.add(entry2)
        await db_session.flush()

        # PATCH entry2 start to 8PM — now overlaps with entry1
        response = await auth_client.patch(
            f"/time-entries/{entry2.id}",
            json={"start_datetime": datetime(2025, 11, 30, 20, 0, 0).isoformat()},
        )
        assert response.status_code == 422

    async def test_patch_does_not_overlap_with_self(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        # Shifting the same entry's end time should not 422 against itself
        response = await auth_client.patch(
            f"/time-entries/{entry.id}",
            json={"end_datetime": datetime(2025, 11, 30, 22, 0, 0).isoformat()},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# DELETE 409 guard (linked batches)
# ---------------------------------------------------------------------------


class TestDeleteTimeEntryGuard:
    async def _seed_sample_type(self, db: AsyncSession) -> SampleType:
        st = SampleType(name="Guard Test Type")
        db.add(st)
        await db.flush()
        return st

    async def test_delete_with_active_batch_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from datetime import date

        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        st = await self._seed_sample_type(db_session)

        batch = SampleBatch(
            sample_type_id=st.id,
            time_entry_id=entry.id,
            batch_num="GUARD-001",
            date_collected=date(2025, 11, 30),
            status=SampleBatchStatus.ACTIVE,
        )
        db_session.add(batch)
        await db_session.flush()

        response = await auth_client.delete(f"/time-entries/{entry.id}")
        assert response.status_code == 409

    async def test_delete_with_discarded_batch_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from datetime import date

        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        st = await self._seed_sample_type(db_session)

        batch = SampleBatch(
            sample_type_id=st.id,
            time_entry_id=entry.id,
            batch_num="GUARD-002",
            date_collected=date(2025, 11, 30),
            status=SampleBatchStatus.DISCARDED,
        )
        db_session.add(batch)
        await db_session.flush()

        response = await auth_client.delete(f"/time-entries/{entry.id}")
        assert response.status_code == 409

    async def test_delete_with_no_batches_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        response = await auth_client.delete(f"/time-entries/{entry.id}")
        assert response.status_code == 204
