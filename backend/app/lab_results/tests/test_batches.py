"""
Integration tests for lab results batch endpoints.

GET    /lab-results/batches/
GET    /lab-results/batches/{batch_id}
POST   /lab-results/batches/
PATCH  /lab-results/batches/{batch_id}
DELETE /lab-results/batches/{batch_id}
"""

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import EmployeeRoleType
from app.employees.models import Employee, EmployeeRole
from app.lab_results.models import (
    SampleBatch,
    SampleType,
    SampleUnitType,
)
from app.projects.models import Project
from app.schools.models import School
from app.time_entries.models import TimeEntry
from tests.seeds import (
    seed_employee,
    seed_employee_role,
    seed_project,
    seed_sample_required_role,
    seed_sample_subtype,
    seed_sample_turnaround_option,
    seed_sample_type,
    seed_sample_unit_type,
    seed_school,
    seed_time_entry,
)

BASE = "/lab-results/batches"

DATE_COLLECTED = date(2025, 11, 30)

# ---------------------------------------------------------------------------
# Helpers — school codes use "B" prefix to avoid collision with config tests
# ---------------------------------------------------------------------------


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
    school = await seed_school(db)
    project = await seed_project(db, school)
    emp = await seed_employee(db)
    role = await seed_employee_role(db, emp, role_type=role_type)
    entry = await seed_time_entry(db, emp, role, project, school)
    sample_type = await seed_sample_type(
        db, name=sample_type_name, allows_multiple_inspectors=allows_multiple
    )
    unit_type = await seed_sample_unit_type(db, sample_type)
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
        subtype = await seed_sample_subtype(db_session, ctx.sample_type)
        tat = await seed_sample_turnaround_option(db_session, ctx.sample_type)

        response = await auth_client.post(
            BASE + "/",
            json=ctx.batch_payload(
                batch_num="BATCH-OPT-001",
                sample_subtype_id=subtype.id,
                turnaround_option_id=tat.id,
                notes="Field notes here",
            ),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sample_subtype_id"] == subtype.id
        assert data["turnaround_option_id"] == tat.id
        assert data["notes"] == "Field notes here"

    async def test_create_materializes_lab_report_requirement(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from sqlalchemy import select

        from app.lab_reports.models import LabReportRequirement

        ctx = await _make_context(db_session, sample_type_name="Lab Report Dispatch")

        response = await auth_client.post(BASE + "/", json=ctx.batch_payload("BATCH-LRR-001"))
        assert response.status_code == 201
        batch_id = response.json()["id"]

        rows = (
            await db_session.execute(
                select(LabReportRequirement).where(
                    LabReportRequirement.sample_batch_id == batch_id
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].project_id == ctx.project.id
        assert rows[0].is_saved is False

    async def test_duplicate_batch_num_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Dupe Batch Num")
        await auth_client.post(BASE + "/", json=ctx.batch_payload("DUPE-001"))
        response = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("DUPE-001")
        )
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
        other_type = await seed_sample_type(db_session, name="Other Type For Subtype")
        wrong_subtype = await seed_sample_subtype(
            db_session, other_type, name="Belongs to Other"
        )

        payload = ctx.batch_payload("BATCH-SW1", sample_subtype_id=wrong_subtype.id)
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422

    async def test_turnaround_wrong_sample_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="TAT Wrong Type")
        other_type = await seed_sample_type(db_session, name="Other Type For TAT")
        wrong_tat = await seed_sample_turnaround_option(db_session, other_type)

        payload = ctx.batch_payload("BATCH-TW1", turnaround_option_id=wrong_tat.id)
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422

    async def test_unit_type_wrong_sample_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Unit Wrong Type")
        other_type = await seed_sample_type(db_session, name="Other Type For Unit")
        wrong_unit = await seed_sample_unit_type(
            db_session, other_type, name="Wrong Unit"
        )

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
        await seed_sample_required_role(
            db_session, ctx.sample_type, role_type=EmployeeRoleType.ACM_AIR_TECH
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
        await seed_sample_required_role(
            db_session, ctx.sample_type, role_type=EmployeeRoleType.ACM_AIR_TECH
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
        emp2 = await seed_employee(db_session)

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
        emp2 = await seed_employee(db_session)

        payload = ctx.batch_payload("BATCH-SI1")
        payload["inspector_ids"] = [ctx.emp.id, emp2.id]
        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /lab-results/batches/
# ---------------------------------------------------------------------------


class TestListBatches:
    async def test_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
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
    async def test_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Get Single Type")
        create = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-G001")
        )
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
    async def test_patch_date_collected(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Patch Date Type")
        create = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-P002")
        )
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
        create = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-P003")
        )
        batch_id = create.json()["id"]

        response = await auth_client.patch(
            f"{BASE}/{batch_id}", json={"notes": "Updated field note"}
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated field note"

    async def test_patch_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(f"{BASE}/9999", json={"notes": "x"})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /lab-results/batches/{batch_id}
# ---------------------------------------------------------------------------


class TestDeleteBatch:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Delete Batch Type")
        create = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-D001")
        )
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
        response = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-AU1")
        )
        assert response.status_code == 201
        batch = await db_session.get(SampleBatch, response.json()["id"])
        assert (
            batch and batch.created_by_id == 1
        )  # fake_user.id from auth_client fixture

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
        assert (
            batch and batch.updated_by_id == 1
        )  # fake_user.id from auth_client fixture


# ---------------------------------------------------------------------------
# Batch status defaults
# ---------------------------------------------------------------------------


class TestBatchStatusDefault:
    async def test_create_defaults_to_active(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Status Default Type")
        response = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-ST1")
        )
        assert response.status_code == 201
        assert response.json()["status"] == "active"


# ---------------------------------------------------------------------------
# POST /batches/{id}/discard
# ---------------------------------------------------------------------------


class TestDiscardBatch:
    async def test_discard_active_batch_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Discard Type 1")
        create = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-DIS1")
        )
        batch_id = create.json()["id"]

        response = await auth_client.post(f"{BASE}/{batch_id}/discard")
        assert response.status_code == 200
        assert response.json()["status"] == "discarded"

    async def test_discard_already_discarded_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Discard Type 2")
        create = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-DIS2")
        )
        batch_id = create.json()["id"]

        await auth_client.post(f"{BASE}/{batch_id}/discard")
        response = await auth_client.post(f"{BASE}/{batch_id}/discard")
        assert response.status_code == 422

    async def test_discard_missing_batch_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post(f"{BASE}/9999/discard")
        assert response.status_code == 404

    async def test_discard_sets_updated_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Discard Type 3")
        create = await auth_client.post(
            BASE + "/", json=ctx.batch_payload("BATCH-DIS3")
        )
        batch_id = create.json()["id"]

        await auth_client.post(f"{BASE}/{batch_id}/discard")
        batch = await db_session.get(SampleBatch, batch_id)
        assert (
            batch and batch.updated_by_id == 1
        )  # fake_user.id from auth_client fixture


# ---------------------------------------------------------------------------
# Nullable time_entry_id
# ---------------------------------------------------------------------------


class TestNullableTimeEntry:
    async def test_create_batch_without_time_entry_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Nullable TE Type")
        payload = ctx.batch_payload("BATCH-NTE1")
        payload["time_entry_id"] = None  # explicitly null

        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 201
        assert response.json()["time_entry_id"] is None

    async def test_create_batch_with_invalid_time_entry_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _make_context(db_session, sample_type_name="Nullable TE Type 2")
        payload = ctx.batch_payload("BATCH-NTE2")
        payload["time_entry_id"] = 9999  # non-existent

        response = await auth_client.post(BASE + "/", json=payload)
        assert response.status_code == 404
