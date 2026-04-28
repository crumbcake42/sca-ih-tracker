"""
Integration tests for the quick-add batch endpoint.

POST /lab-results/batches/quick-add
  Creates a TimeEntry (status=assumed, start=midnight of date_on_site, end=None,
  created_by_id=SYSTEM_USER_ID) and a SampleBatch atomically.
"""

from datetime import date, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import Boro, TimeEntryStatus
from app.employees.models import Employee, EmployeeRole
from app.lab_results.models import SampleType, SampleUnitType
from app.projects.models import Project
from app.schools.models import School
from app.time_entries.models import TimeEntry
from tests.seeds import (
    seed_employee,
    seed_employee_role,
    seed_project,
    seed_sample_type,
    seed_sample_unit_type,
    seed_school,
)

BASE = "/lab-results/batches/quick-add"

DATE_ON_SITE = date(2025, 12, 1)
DATE_COLLECTED = date(2025, 12, 1)

_counter = iter(range(1, 9999))


def _code() -> str:
    return f"QA{next(_counter):03d}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _QAContext:
    def __init__(
        self,
        school: School,
        project: Project,
        emp: Employee,
        role: EmployeeRole,
        sample_type: SampleType,
        unit_type: SampleUnitType,
    ):
        self.school = school
        self.project = project
        self.emp = emp
        self.role = role
        self.sample_type = sample_type
        self.unit_type = unit_type

    def payload(self, batch_num: str = "QA-BATCH-001", **overrides) -> dict:
        return {
            "employee_id": self.emp.id,
            "employee_role_id": self.role.id,
            "project_id": self.project.id,
            "school_id": self.school.id,
            "date_on_site": DATE_ON_SITE.isoformat(),
            "sample_type_id": self.sample_type.id,
            "batch_num": batch_num,
            "date_collected": DATE_COLLECTED.isoformat(),
            "units": [{"sample_unit_type_id": self.unit_type.id, "quantity": 3}],
            "inspector_ids": [self.emp.id],
            **overrides,
        }


async def _make_context(db: AsyncSession) -> _QAContext:
    school = await seed_school(db)
    project = await seed_project(db, school)
    emp = await seed_employee(db)
    role = await seed_employee_role(db, emp)
    sample_type = await seed_sample_type(db)
    unit_type = await seed_sample_unit_type(db, sample_type)
    return _QAContext(school, project, emp, role, sample_type, unit_type)


# ---------------------------------------------------------------------------
# POST /lab-results/batches/quick-add
# ---------------------------------------------------------------------------


class TestQuickAdd:
    async def test_happy_path_creates_batch_and_time_entry(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)
        response = await auth_client.post(BASE, json=ctx.payload("QA-001"))
        assert response.status_code == 201
        data = response.json()
        assert data["batch_num"] == "QA-001"
        assert data["status"] == "active"
        assert data["time_entry_id"] is not None

        # Time entry should be assumed and created by SYSTEM_USER_ID
        entry = await db_session.get(TimeEntry, data["time_entry_id"])
        assert entry is not None
        assert entry.status == TimeEntryStatus.ASSUMED
        assert entry.created_by_id == SYSTEM_USER_ID
        assert entry.end_datetime is None
        assert entry.start_datetime == datetime(
            DATE_ON_SITE.year, DATE_ON_SITE.month, DATE_ON_SITE.day
        )

    async def test_assumed_entry_created_with_system_user(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)
        response = await auth_client.post(BASE, json=ctx.payload("QA-002"))
        assert response.status_code == 201

        entry = await db_session.get(TimeEntry, response.json()["time_entry_id"])
        assert entry and entry.created_by_id == SYSTEM_USER_ID

    async def test_missing_employee_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)
        response = await auth_client.post(
            BASE, json=ctx.payload("QA-003", employee_id=9999)
        )
        assert response.status_code == 404

    async def test_missing_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)
        response = await auth_client.post(
            BASE, json=ctx.payload("QA-004", project_id=9999)
        )
        assert response.status_code == 404

    async def test_school_not_on_project_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)
        # Add a second school not linked to the project
        other_school = School(
            code=_code(),
            name="Other School",
            address="2 Other Ave",
            city=Boro.BROOKLYN,
            state="NY",
            zip_code="11201",
        )
        db_session.add(other_school)
        await db_session.flush()

        response = await auth_client.post(
            BASE, json=ctx.payload("QA-005", school_id=other_school.id)
        )
        assert response.status_code == 422

    async def test_overlap_with_existing_entry_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)

        # Seed an existing assumed entry for the same employee on the same date
        midnight = datetime(DATE_ON_SITE.year, DATE_ON_SITE.month, DATE_ON_SITE.day)
        existing = TimeEntry(
            start_datetime=midnight,
            end_datetime=None,
            employee_id=ctx.emp.id,
            employee_role_id=ctx.role.id,
            project_id=ctx.project.id,
            school_id=ctx.school.id,
            status=TimeEntryStatus.ASSUMED,
        )
        db_session.add(existing)
        await db_session.flush()

        response = await auth_client.post(BASE, json=ctx.payload("QA-006"))
        assert response.status_code == 422

    async def test_duplicate_batch_num_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)
        ctx2 = await _make_context(db_session)

        await auth_client.post(BASE, json=ctx.payload("QA-DUP"))
        # Different employee/project but same batch_num
        response = await auth_client.post(BASE, json=ctx2.payload("QA-DUP"))
        assert response.status_code == 409

    async def test_invalid_unit_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)
        payload = ctx.payload("QA-007")
        payload["units"] = [{"sample_unit_type_id": 9999, "quantity": 1}]
        response = await auth_client.post(BASE, json=payload)
        assert response.status_code == 404

    async def test_missing_inspector_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session)
        payload = ctx.payload("QA-008")
        payload["inspector_ids"] = [9999]
        response = await auth_client.post(BASE, json=payload)
        assert response.status_code == 404
