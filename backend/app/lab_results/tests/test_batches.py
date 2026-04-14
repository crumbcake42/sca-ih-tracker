"""
Integration tests for lab results batch endpoints.

GET    /lab-results/batches/
GET    /lab-results/batches/{batch_id}
POST   /lab-results/batches/
PATCH  /lab-results/batches/{batch_id}
DELETE /lab-results/batches/{batch_id}
"""

from datetime import date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro, EmployeeRoleType
from app.employees.models import Employee, EmployeeRole
from app.lab_results.models import (
    SampleBatch,
    SampleBatchInspector,
    SampleBatchUnit,
    SampleSubtype,
    SampleType,
    SampleTypeRequiredRole,
    SampleUnitType,
    TurnaroundOption,
)
from app.projects.models import Project
from app.schools.models import School
from app.time_entries.models import TimeEntry

BASE = "/lab-results/batches"

DT_START = datetime(2025, 11, 30, 9, 0, 0)
DT_END = datetime(2025, 11, 30, 17, 0, 0)
DATE_COLLECTED = date(2025, 11, 30)

# ---------------------------------------------------------------------------
# Helpers — school codes use "B" prefix to avoid collision with config tests
# ---------------------------------------------------------------------------

_school_counter = iter(range(1, 9999))


def _next_school_code() -> str:
    return f"B{next(_school_counter):03d}"


async def _seed_school(db: AsyncSession, code: str | None = None) -> School:
    school = School(
        code=code or _next_school_code(),
        name=f"School {code or _next_school_code()}",
        address="1 Test Ave",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()
    return school


async def _seed_project(db: AsyncSession, school: School) -> Project:
    project = Project(name="Batch Test Project", project_number=f"25-B{school.id:04d}")
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


async def _seed_employee(db: AsyncSession) -> Employee:
    emp = Employee(first_name="Jane", last_name="Doe")
    db.add(emp)
    await db.flush()
    return emp


async def _seed_role(
    db: AsyncSession,
    employee: Employee,
    role_type: EmployeeRoleType = EmployeeRoleType.ACM_AIR_TECH,
    start: date = date(2025, 1, 1),
    end: date | None = None,
) -> EmployeeRole:
    role = EmployeeRole(
        employee_id=employee.id,
        role_type=role_type,
        start_date=start,
        end_date=end,
        hourly_rate="75.00",
    )
    db.add(role)
    await db.flush()
    return role


async def _seed_entry(
    db: AsyncSession,
    employee: Employee,
    role: EmployeeRole,
    project: Project,
    school: School,
) -> TimeEntry:
    entry = TimeEntry(
        start_datetime=DT_START,
        end_datetime=DT_END,
        employee_id=employee.id,
        employee_role_id=role.id,
        project_id=project.id,
        school_id=school.id,
    )
    db.add(entry)
    await db.flush()
    return entry


async def _seed_sample_type(
    db: AsyncSession,
    name: str = "Asbestos Air",
    allows_multiple: bool = True,
) -> SampleType:
    st = SampleType(name=name, allows_multiple_inspectors=allows_multiple)
    db.add(st)
    await db.flush()
    return st


async def _seed_unit_type(
    db: AsyncSession, sample_type: SampleType, name: str = "PCM Sample"
) -> SampleUnitType:
    ut = SampleUnitType(sample_type_id=sample_type.id, name=name)
    db.add(ut)
    await db.flush()
    return ut


async def _seed_subtype(
    db: AsyncSession, sample_type: SampleType, name: str = "Friable"
) -> SampleSubtype:
    st = SampleSubtype(sample_type_id=sample_type.id, name=name)
    db.add(st)
    await db.flush()
    return st


async def _seed_tat(
    db: AsyncSession, sample_type: SampleType, hours: int = 24, label: str = "Standard"
) -> TurnaroundOption:
    tat = TurnaroundOption(sample_type_id=sample_type.id, hours=hours, label=label)
    db.add(tat)
    await db.flush()
    return tat


async def _seed_required_role(
    db: AsyncSession,
    sample_type: SampleType,
    role_type: EmployeeRoleType = EmployeeRoleType.ACM_AIR_TECH,
) -> SampleTypeRequiredRole:
    rr = SampleTypeRequiredRole(
        sample_type_id=sample_type.id, role_type=role_type
    )
    db.add(rr)
    await db.flush()
    return rr


# Full happy-path context: school, project, employee, role, time entry, sample type
class _BatchContext:
    def __init__(
        self,
        school: School,
        project: Project,
        emp: Employee,
        role: EmployeeRole,
        entry: TimeEntry,
        sample_type: SampleType,
        unit_type: SampleUnitType,
    ):
        self.school = school
        self.project = project
        self.emp = emp
        self.role = role
        self.entry = entry
        self.sample_type = sample_type
        self.unit_type = unit_type

    def batch_payload(
        self,
        batch_num: str = "BATCH-001",
        **overrides,
    ) -> dict:
        return {
            "sample_type_id": self.sample_type.id,
            "time_entry_id": self.entry.id,
            "batch_num": batch_num,
            "date_collected": DATE_COLLECTED.isoformat(),
            "units": [{"sample_unit_type_id": self.unit_type.id, "quantity": 5}],
            "inspector_ids": [self.emp.id],
            **overrides,
        }


async def _make_context(
    db: AsyncSession,
    role_type: EmployeeRoleType = EmployeeRoleType.ACM_AIR_TECH,
    sample_type_name: str = "Asbestos Air",
    allows_multiple: bool = True,
) -> _BatchContext:
    school = await _seed_school(db)
    project = await _seed_project(db, school)
    emp = await _seed_employee(db)
    role = await _seed_role(db, emp, role_type=role_type)
    entry = await _seed_entry(db, emp, role, project, school)
    sample_type = await _seed_sample_type(db, sample_type_name, allows_multiple)
    unit_type = await _seed_unit_type(db, sample_type)
    return _BatchContext(school, project, emp, role, entry, sample_type, unit_type)


# ---------------------------------------------------------------------------
# POST /lab-results/batches/
# ---------------------------------------------------------------------------


class TestCreateBatch:
    async def test_create_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Create Happy Path")
        response = await auth_client.post(BASE + "/", json=ctx.batch_payload())
        assert response.status_code == 201
        data = response.json()
        assert data["sample_type_id"] == ctx.sample_type.id
        assert data["time_entry_id"] == ctx.entry.id
        assert data["batch_num"] == "BATCH-001"
        assert len(data["units"]) == 1
        assert data["units"][0]["quantity"] == 5
        assert len(data["inspectors"]) == 1
        assert data["inspectors"][0]["employee_id"] == ctx.emp.id

    async def test_create_with_optional_fields(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Create Optional Fields")
        subtype = await _seed_subtype(db_session, ctx.sample_type)
        tat = await _seed_tat(db_session, ctx.sample_type)

        response = await auth_client.post(
            BASE + "/",
            json=ctx.batch_payload(
                batch_num="BATCH-OPT-001",
                sample_subtype_id=subtype.id,
                turnaround_option_id=tat.id,
                notes="Field notes here",
                is_report=True,
            ),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sample_subtype_id"] == subtype.id
        assert data["turnaround_option_id"] == tat.id
        assert data["notes"] == "Field notes here"
        assert data["is_report"] is True

    async def test_duplicate_batch_num_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Dupe Batch Num")
        await auth_client.post(BASE + "/", json=ctx.batch_payload("DUPE-001"))
        response = await auth_client.post(BASE + "/", json=ctx.batch_payload("DUPE-001"))
        assert response.status_code == 409

    async def test_missing_sample_type_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Missing Type Test")
        payload = ctx.batch_payload("BATCH-M1")
        payload["sample_type_id"] = 9999
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 404

    async def test_missing_time_entry_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Missing Entry Test")
        payload = ctx.batch_payload("BATCH-M2")
        payload["time_entry_id"] = 9999
        response = await auth_client.post(BASE + "/", json=payload)
        # validate_employee_role_for_sample_type returns 404 when time entry not found
        assert response.status_code == 404

    async def test_missing_employee_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Missing Emp Test")
        payload = ctx.batch_payload("BATCH-M3")
        payload["inspector_ids"] = [9999]
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 404

    async def test_empty_units_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Empty Units Test")
        payload = ctx.batch_payload("BATCH-EU1")
        payload["units"] = []
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422

    async def test_empty_inspector_ids_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Empty Inspectors Test")
        payload = ctx.batch_payload("BATCH-EI1")
        payload["inspector_ids"] = []
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422

    async def test_unit_quantity_zero_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Zero Qty Test")
        payload = ctx.batch_payload("BATCH-ZQ1")
        payload["units"] = [{"sample_unit_type_id": ctx.unit_type.id, "quantity": 0}]
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422


class TestCreateBatchValidation:
    """Tests for cross-entity validation in batch creation."""

    async def test_subtype_wrong_sample_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Subtype Wrong Type")
        other_type = await _seed_sample_type(db_session, "Other Type For Subtype")
        wrong_subtype = await _seed_subtype(db_session, other_type, "Belongs to Other")

        payload = ctx.batch_payload("BATCH-SW1", sample_subtype_id=wrong_subtype.id)
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422

    async def test_turnaround_wrong_sample_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="TAT Wrong Type")
        other_type = await _seed_sample_type(db_session, "Other Type For TAT")
        wrong_tat = await _seed_tat(db_session, other_type)

        payload = ctx.batch_payload("BATCH-TW1", turnaround_option_id=wrong_tat.id)
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422

    async def test_unit_type_wrong_sample_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Unit Wrong Type")
        other_type = await _seed_sample_type(db_session, "Other Type For Unit")
        wrong_unit = await _seed_unit_type(db_session, other_type, "Wrong Unit")

        payload = ctx.batch_payload("BATCH-UW1")
        payload["units"] = [{"sample_unit_type_id": wrong_unit.id, "quantity": 3}]
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422

    async def test_employee_role_mismatch_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # Sample type requires ACM_AIR_TECH; employee has ACM_PROJECT_MONITOR
        ctx = await _make_context(
            db_session,
            role_type=EmployeeRoleType.ACM_PROJECT_MONITOR,
            sample_type_name="Role Mismatch Type",
        )
        await _seed_required_role(
            db_session, ctx.sample_type, EmployeeRoleType.ACM_AIR_TECH
        )

        response = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-RM1")
        )
        assert response.status_code == 422

    async def test_employee_role_match_allowed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # Sample type requires ACM_AIR_TECH; employee has ACM_AIR_TECH
        ctx = await _make_context(
            db_session,
            role_type=EmployeeRoleType.ACM_AIR_TECH,
            sample_type_name="Role Match Type",
        )
        await _seed_required_role(
            db_session, ctx.sample_type, EmployeeRoleType.ACM_AIR_TECH
        )

        response = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-RO1")
        )
        assert response.status_code == 201

    async def test_no_required_roles_any_employee_allowed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # Sample type has no required roles — any employee role should work
        ctx = await _make_context(
            db_session,
            role_type=EmployeeRoleType.ACM_PROJECT_MONITOR,
            sample_type_name="No Role Restriction",
        )
        # No required roles seeded for this sample type

        response = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-NR1")
        )
        assert response.status_code == 201

    async def test_multiple_inspectors_allowed_when_flag_true(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(
            db_session,
            sample_type_name="Multi Inspector OK",
            allows_multiple=True,
        )
        emp2 = await _seed_employee(db_session)

        payload = ctx.batch_payload("BATCH-MI1")
        payload["inspector_ids"] = [ctx.emp.id, emp2.id]
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 201
        assert len(response.json()["inspectors"]) == 2

    async def test_multiple_inspectors_rejected_when_flag_false(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(
            db_session,
            sample_type_name="Single Inspector Only",
            allows_multiple=False,
        )
        emp2 = await _seed_employee(db_session)

        payload = ctx.batch_payload("BATCH-SI1")
        payload["inspector_ids"] = [ctx.emp.id, emp2.id]
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /lab-results/batches/
# ---------------------------------------------------------------------------


class TestListBatches:
    async def test_returns_200(self, auth_client: AsyncClient, db_session: AsyncSession):
        ctx = await _make_context(db_session, sample_type_name="List Test Type")
        await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-L001"))

        response = await auth_client.get(BASE + "/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_filter_by_sample_type_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Filter By Type")
        await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-FT1"))

        response = await auth_client.get(
            BASE + "/", params={"sample_type_id": ctx.sample_type.id}
        )
        assert response.status_code == 200
        data = response.json()
        assert all(b["sample_type_id"] == ctx.sample_type.id for b in data)

    async def test_filter_by_time_entry_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Filter By Entry")
        await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-FE1"))

        response = await auth_client.get(
            BASE + "/", params={"time_entry_id": ctx.entry.id}
        )
        assert response.status_code == 200
        data = response.json()
        assert all(b["time_entry_id"] == ctx.entry.id for b in data)


# ---------------------------------------------------------------------------
# GET /lab-results/batches/{batch_id}
# ---------------------------------------------------------------------------


class TestGetBatch:
    async def test_returns_200(self, auth_client: AsyncClient, db_session: AsyncSession):
        ctx = await _make_context(db_session, sample_type_name="Get Single Type")
        create = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-G001"))
        batch_id = create.json()["id"]

        response = await auth_client.get(f"{BASE}/{batch_id}")
        assert response.status_code == 200
        assert response.json()["id"] == batch_id

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get(f"{BASE}/9999")
        assert response.status_code == 404

    async def test_response_includes_units_and_inspectors(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Get With Children Type")
        create = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-GC1"))
        batch_id = create.json()["id"]

        response = await auth_client.get(f"{BASE}/{batch_id}")
        data = response.json()
        assert len(data["units"]) == 1
        assert len(data["inspectors"]) == 1


# ---------------------------------------------------------------------------
# PATCH /lab-results/batches/{batch_id}
# ---------------------------------------------------------------------------


class TestUpdateBatch:
    async def test_patch_is_report(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Patch is_report Type")
        create = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-P001"))
        batch_id = create.json()["id"]

        response = await auth_client.patch(
            f"{BASE}/{batch_id}", json={"is_report": True}
        )
        assert response.status_code == 200
        assert response.json()["is_report"] is True

    async def test_patch_date_collected(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Patch Date Type")
        create = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-P002"))
        batch_id = create.json()["id"]

        new_date = date(2025, 12, 1).isoformat()
        response = await auth_client.patch(
            f"{BASE}/{batch_id}", json={"date_collected": new_date}
        )
        assert response.status_code == 200
        assert response.json()["date_collected"] == new_date

    async def test_patch_notes(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Patch Notes Type")
        create = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-P003"))
        batch_id = create.json()["id"]

        response = await auth_client.patch(
            f"{BASE}/{batch_id}", json={"notes": "Updated field note"}
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated field note"

    async def test_patch_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            f"{BASE}/9999", json={"is_report": True}
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /lab-results/batches/{batch_id}
# ---------------------------------------------------------------------------


class TestDeleteBatch:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Delete Batch Type")
        create = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-D001"))
        batch_id = create.json()["id"]

        response = await auth_client.delete(f"{BASE}/{batch_id}")
        assert response.status_code == 204

        follow_up = await auth_client.get(f"{BASE}/{batch_id}")
        assert follow_up.status_code == 404

    async def test_delete_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete(f"{BASE}/9999")
        assert response.status_code == 404

    async def test_delete_cascades_units_and_inspectors(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Delete Cascade Type")
        create = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-DC1"))
        batch_id = create.json()["id"]

        await auth_client.delete(f"{BASE}/{batch_id}")

        # After delete, units and inspectors should be gone via cascade.
        # Verify by checking the batch itself is gone.
        batch = await db_session.get(SampleBatch, batch_id)
        assert batch is None


# ---------------------------------------------------------------------------
# Audit field wiring
# ---------------------------------------------------------------------------


class TestBatchAuditFields:
    async def test_create_sets_created_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Audit Create Type")
        response = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-AU1"))
        assert response.status_code == 201
        batch = await db_session.get(SampleBatch, response.json()["id"])
        assert batch.created_by_id == 1  # fake_user.id from auth_client fixture

    async def test_update_sets_updated_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Audit Update Type")
        create = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-AU2"))
        batch_id = create.json()["id"]

        response = await auth_client.patch(
            f"{BASE}/{batch_id}", json={"notes": "audit test"}
        )
        assert response.status_code == 200
        batch = await db_session.get(SampleBatch, batch_id)
        assert batch.updated_by_id == 1  # fake_user.id from auth_client fixture
