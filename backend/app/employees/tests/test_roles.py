"""
Integration tests for employee role management.

The overlap check in POST /employees/{id}/roles is the most important piece
of business logic in this codebase. It lives in the router and requires a DB
query, so it can't be covered by the schema unit tests in test_schemas.py.

Each test case here maps to a distinct branch of the overlap SQL condition:

  start_date <= (new.end_date or 9999-01-01)   -- existing role starts before new role ends
  AND (end_date IS NULL OR end_date >= new.start_date)  -- existing role ends after new role starts
"""

from datetime import date
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import EmployeeRoleType
from app.employees.models import Employee, EmployeeRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_employee(db: AsyncSession, **overrides) -> Employee:
    first = overrides.get("first_name", "Jane")
    last = overrides.get("last_name", "Doe")
    defaults = dict(first_name=first, last_name=last, display_name=f"{first} {last}")
    emp = Employee(**{**defaults, **overrides})
    db.add(emp)
    await db.flush()
    return emp


async def _seed_role(
    db: AsyncSession,
    employee_id: int,
    role_type: EmployeeRoleType = EmployeeRoleType.ACM_AIR_TECH,
    **overrides,
) -> EmployeeRole:
    defaults: dict = dict(
        role_type=role_type,
        start_date=date(2024, 1, 1),
        end_date=None,
        hourly_rate=Decimal("25.00"),
    )
    for field in ("start_date", "end_date"):
        if field in overrides and isinstance(overrides[field], str):
            overrides[field] = date.fromisoformat(overrides[field])
    role = EmployeeRole(employee_id=employee_id, **{**defaults, **overrides})
    db.add(role)
    await db.flush()
    return role


def _role_payload(
    role_type: EmployeeRoleType = EmployeeRoleType.ACM_AIR_TECH, **overrides
) -> dict:
    defaults = dict(
        role_type=role_type.value,
        start_date="2024-07-01",
        end_date=None,
        hourly_rate="30.00",
    )
    return {**defaults, **overrides}


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


class TestEmployeeRoleCRUD:
    async def test_create_role_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session)
        response = await auth_client.post(
            f"/employees/{emp.id}/roles", json=_role_payload()
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role_type"] == EmployeeRoleType.ACM_AIR_TECH.value
        assert data["employee_id"] == emp.id

    async def test_list_roles_returns_sorted_by_start_date(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session)
        await _seed_role(
            db_session, emp.id, start_date="2024-06-01", end_date="2024-09-01"
        )
        await _seed_role(
            db_session,
            emp.id,
            start_date="2023-01-01",
            end_date="2023-12-31",
        )
        response = await auth_client.get(f"/employees/{emp.id}/roles")
        assert response.status_code == 200
        dates = [r["start_date"] for r in response.json()]
        assert dates == sorted(dates)

    async def test_create_role_for_missing_employee_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        response = await auth_client.post(
            "/employees/9999/roles", json=_role_payload()
        )
        assert response.status_code == 404

    async def test_delete_role(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session)
        role = await _seed_role(db_session, emp.id)
        response = await auth_client.delete(f"/employees/roles/{role.id}")
        assert response.status_code == 204

    async def test_delete_missing_role_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/employees/roles/9999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Overlap detection — the core business rule
# ---------------------------------------------------------------------------
# Diagram key:  [===] = existing role date range,  <----> = new role attempt
#
# Each test name describes the geometric relationship between the two ranges.


class TestRoleOverlap:
    """
    All tests seed one closed role [Jan–Mar] of the same type,
    then attempt to add a second role of the same type that varies in position.
    """

    async def test_overlap_completely_inside_existing(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # [=======Jan–Mar=======]
        #       <--Feb-->
        emp = await _seed_employee(db_session)
        await _seed_role(
            db_session, emp.id, start_date="2024-01-01", end_date="2024-03-31"
        )
        payload = _role_payload(start_date="2024-02-01", end_date="2024-02-28")
        response = await auth_client.post(f"/employees/{emp.id}/roles", json=payload)
        assert response.status_code == 409

    async def test_overlap_new_starts_before_existing_ends(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # [=====Jan–Mar=====]
        #                <--Mar–May-->
        emp = await _seed_employee(db_session)
        await _seed_role(
            db_session, emp.id, start_date="2024-01-01", end_date="2024-03-31"
        )
        payload = _role_payload(start_date="2024-03-01", end_date="2024-05-31")
        response = await auth_client.post(f"/employees/{emp.id}/roles", json=payload)
        assert response.status_code == 409

    async def test_overlap_new_starts_exactly_on_end_date_of_existing(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # [=====Jan–Mar=====]
        #                   <--Mar 31–May-->
        # The overlap condition uses >= on end_date, so Mar 31 == Mar 31 overlaps.
        emp = await _seed_employee(db_session)
        await _seed_role(
            db_session, emp.id, start_date="2024-01-01", end_date="2024-03-31"
        )
        payload = _role_payload(start_date="2024-03-31", end_date="2024-05-31")
        response = await auth_client.post(f"/employees/{emp.id}/roles", json=payload)
        assert response.status_code == 409

    async def test_overlap_existing_is_open_ended(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # [=====Jan–∞=====]
        #             <--Jul–Dec-->
        emp = await _seed_employee(db_session)
        await _seed_role(db_session, emp.id, start_date="2024-01-01", end_date=None)
        payload = _role_payload(start_date="2024-07-01", end_date="2024-12-31")
        response = await auth_client.post(f"/employees/{emp.id}/roles", json=payload)
        assert response.status_code == 409

    async def test_no_overlap_new_is_entirely_after_existing(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # [=====Jan–Mar=====]
        #                       <--May–Jul-->
        emp = await _seed_employee(db_session)
        await _seed_role(
            db_session, emp.id, start_date="2024-01-01", end_date="2024-03-31"
        )
        payload = _role_payload(start_date="2024-05-01", end_date="2024-07-31")
        response = await auth_client.post(f"/employees/{emp.id}/roles", json=payload)
        assert response.status_code == 201

    async def test_no_overlap_new_is_entirely_before_existing(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        #                   [=====Jul–Dec=====]
        # <--Jan–Mar-->
        emp = await _seed_employee(db_session)
        await _seed_role(
            db_session, emp.id, start_date="2024-07-01", end_date="2024-12-31"
        )
        payload = _role_payload(start_date="2024-01-01", end_date="2024-03-31")
        response = await auth_client.post(f"/employees/{emp.id}/roles", json=payload)
        assert response.status_code == 201

    async def test_different_role_types_do_not_conflict(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # Overlap check is per role_type. Two different role types
        # can cover the same date range for the same employee.
        emp = await _seed_employee(db_session)
        await _seed_role(
            db_session,
            emp.id,
            role_type=EmployeeRoleType.ACM_AIR_TECH,
            start_date="2024-01-01",
            end_date=None,
        )
        payload = _role_payload(
            role_type=EmployeeRoleType.ACM_PROJECT_MONITOR,
            start_date="2024-01-01",
            end_date=None,
        )
        response = await auth_client.post(f"/employees/{emp.id}/roles", json=payload)
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# PATCH /employees/roles/{role_id}
# ---------------------------------------------------------------------------


class TestUpdateRole:
    async def test_patch_end_date(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session)
        role = await _seed_role(
            db_session, emp.id, start_date="2024-01-01", end_date=None
        )
        response = await auth_client.patch(
            f"/employees/roles/{role.id}",
            json={"end_date": "2024-06-30"},
        )
        assert response.status_code == 200
        assert response.json()["end_date"] == "2024-06-30"

    async def test_patch_end_date_before_start_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session)
        role = await _seed_role(
            db_session, emp.id, start_date="2024-06-01", end_date=None
        )
        response = await auth_client.patch(
            f"/employees/roles/{role.id}",
            json={"end_date": "2024-01-01"},
        )
        assert response.status_code == 422

    async def test_patch_missing_role_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            "/employees/roles/9999", json={"end_date": "2024-12-31"}
        )
        assert response.status_code == 404
