"""
Integration tests for the schools router.

Schools use the factory-generated readonly router (create_readonly_router) and
a batch import router (create_batch_import_router). Because the same factory
backs contractors, hygienists, wa_codes, and deliverables, a bug in the
factory will surface here first — and the fix will apply to all of them.

These tests require a real DB session (in-memory SQLite) and a fake
authenticated client. Both come from the root conftest.py.
"""

import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro
from app.schools.models import School

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_school(**overrides) -> School:
    """Return a School ORM object with sensible defaults, easily overridden."""
    defaults = dict(
        code="M134",
        name="P.S. 134",
        address="293 East Broadway",
        city=Boro.MANHATTAN,
        state="NY",
        zip_code="10002",
    )
    return School(**{**defaults, **overrides})


async def _seed(db: AsyncSession, *schools: School) -> list[School]:
    """Persist schools and flush so they get IDs without committing."""
    for s in schools:
        db.add(s)
    await db.flush()
    return list(schools)


# ---------------------------------------------------------------------------
# List endpoint — GET /schools/
# ---------------------------------------------------------------------------
# Why test the list endpoint at all if it's factory-generated?
# The factory wires together get_paginated_list, sorting, search, and the
# PaginatedResponse schema. Any mismatch in that wiring will only show up
# here — the factory unit itself has no tests of its own.

class TestListSchools:
    async def test_empty_db_returns_empty_list(self, auth_client: AsyncClient):
        response = await auth_client.get("/schools/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_returns_seeded_school(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_school())
        response = await auth_client.get("/schools/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["code"] == "M134"

    async def test_pagination_skip(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # Seed two schools; skipping 1 should return only the second.
        await _seed(
            db_session,
            _make_school(code="K001", name="School A"),
            _make_school(code="M002", name="School B"),
        )
        response = await auth_client.get("/schools/?skip=1&limit=1")
        data = response.json()
        assert data["total"] == 2       # total reflects the full count
        assert len(data["items"]) == 1  # only one item returned

    async def test_pagination_limit(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_school(code="K001", name="School A"),
            _make_school(code="M002", name="School B"),
        )
        response = await auth_client.get("/schools/?limit=1")
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1

    async def test_search_filters_by_code(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # The factory uses School.code as the search attribute.
        await _seed(
            db_session,
            _make_school(code="K001", name="Brooklyn School"),
            _make_school(code="M002", name="Manhattan School"),
        )
        response = await auth_client.get("/schools/?search=K00")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["code"] == "K001"

    async def test_search_is_case_insensitive(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_school(code="K001", name="Brooklyn School"))
        response = await auth_client.get("/schools/?search=k001")
        data = response.json()
        assert data["total"] == 1

    async def test_search_no_match_returns_empty(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_school())
        response = await auth_client.get("/schools/?search=ZZZZ")
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.parametrize("limit", [0, 101])
    async def test_invalid_limit_rejected(
        self, auth_client: AsyncClient, limit: int
    ):
        # limit must be between 1 and 100 — the factory enforces this via Query.
        response = await auth_client.get(f"/schools/?limit={limit}")
        assert response.status_code == 422

    async def test_negative_skip_rejected(self, auth_client: AsyncClient):
        response = await auth_client.get("/schools/?skip=-1")
        assert response.status_code == 422

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        # Verify the auth dependency is actually enforced — the unauthenticated
        # client has no token override.
        response = await client.get("/schools/")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Detail endpoint — GET /schools/{identifier}
# ---------------------------------------------------------------------------
# This endpoint is hand-written (not factory-generated) and supports lookup
# by both numeric ID and school code string.

class TestGetSchool:
    async def test_lookup_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school] = await _seed(db_session, _make_school())
        response = await auth_client.get(f"/schools/{school.id}")
        assert response.status_code == 200
        assert response.json()["code"] == "M134"

    async def test_lookup_by_code(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_school())
        response = await auth_client.get("/schools/M134")
        assert response.status_code == 200
        assert response.json()["code"] == "M134"

    async def test_lookup_by_code_case_insensitive(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_school())
        response = await auth_client.get("/schools/m134")
        assert response.status_code == 200

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/schools/9999")
        assert response.status_code == 404

    async def test_unknown_code_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/schools/ZZZZ")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Batch import — POST /schools/batch/import
# ---------------------------------------------------------------------------

def _make_csv(*rows: dict) -> bytes:
    """Build a CSV bytes payload from a list of dicts."""
    import csv
    import io
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode()


_VALID_ROW = dict(
    code="K999",
    name="Test School",
    address="123 Main St",
    city="BROOKLYN",
    state="NY",
    zip_code="11201",
)


class TestBatchImport:
    async def test_valid_csv_creates_school(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        payload = _make_csv(_VALID_ROW)
        response = await auth_client.post(
            "/schools/batch/import",
            files={"file": ("schools.csv", io.BytesIO(payload), "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 1
        assert data["errors"] == []

    async def test_invalid_row_reported_not_raised(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # A bad row (invalid city enum) should produce an error entry, not a 500.
        bad_row = {**_VALID_ROW, "code": "K998", "city": "NOT_A_BORO"}
        payload = _make_csv(bad_row)
        response = await auth_client.post(
            "/schools/batch/import",
            files={"file": ("schools.csv", io.BytesIO(payload), "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 0
        assert len(data["errors"]) == 1
        assert data["errors"][0]["row"] == 2

    async def test_mixed_valid_and_invalid_rows(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # The factory should commit valid rows even when some rows fail.
        # This is the partial-success case that most people forget to test.
        good_row = _VALID_ROW
        bad_row = {**_VALID_ROW, "code": "K998", "city": "INVALID"}
        payload = _make_csv(good_row, bad_row)
        response = await auth_client.post(
            "/schools/batch/import",
            files={"file": ("schools.csv", io.BytesIO(payload), "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 1
        assert len(data["errors"]) == 1

    async def test_duplicate_code_reported_as_error(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_school(code="K999"))
        payload = _make_csv(_VALID_ROW)  # K999 already exists
        response = await auth_client.post(
            "/schools/batch/import",
            files={"file": ("schools.csv", io.BytesIO(payload), "text/csv")},
        )
        data = response.json()
        assert data["created_count"] == 0
        assert len(data["errors"]) == 1

    async def test_non_csv_file_rejected(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/schools/batch/import",
            files={"file": ("schools.txt", io.BytesIO(b"data"), "text/plain")},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /schools/
# ---------------------------------------------------------------------------

_VALID_PAYLOAD = dict(
    code="Q042",
    name="P.S. 42",
    address="71-01 Parsons Blvd",
    city="QUEENS",
    state="NY",
    zip_code="11432",
)


class TestCreateSchool:
    async def test_happy_path_returns_201(self, auth_client: AsyncClient):
        response = await auth_client.post("/schools/", json=_VALID_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "Q042"
        assert "id" in data

    async def test_created_by_id_stamped(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        response = await auth_client.post("/schools/", json=_VALID_PAYLOAD)
        assert response.status_code == 201
        school_id = response.json()["id"]
        result = await db_session.get(School, school_id)
        assert result and result.created_by_id is not None

    async def test_duplicate_code_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_school(code="Q042"))
        response = await auth_client.post("/schools/", json=_VALID_PAYLOAD)
        assert response.status_code == 422

    async def test_code_too_short_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/schools/", json={**_VALID_PAYLOAD, "code": "Q04"}
        )
        assert response.status_code == 422

    async def test_code_too_long_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/schools/", json={**_VALID_PAYLOAD, "code": "Q0420"}
        )
        assert response.status_code == 422

    async def test_invalid_state_too_short_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/schools/", json={**_VALID_PAYLOAD, "state": "N"}
        )
        assert response.status_code == 422

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.post("/schools/", json=_VALID_PAYLOAD)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /schools/{id}
# ---------------------------------------------------------------------------


class TestUpdateSchool:
    async def test_partial_update(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school] = await _seed(db_session, _make_school())
        response = await auth_client.patch(
            f"/schools/{school.id}", json={"name": "Renamed School"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed School"
        assert response.json()["code"] == "M134"  # untouched

    async def test_updated_by_id_stamped(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school] = await _seed(db_session, _make_school())
        await auth_client.patch(
            f"/schools/{school.id}", json={"name": "Renamed School"}
        )
        await db_session.refresh(school)
        assert school.updated_by_id is not None

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch("/schools/9999", json={"name": "X"})
        assert response.status_code == 404

    async def test_patch_code_to_new_value(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school] = await _seed(db_session, _make_school(code="M134"))
        response = await auth_client.patch(
            f"/schools/{school.id}", json={"code": "M999"}
        )
        assert response.status_code == 200
        assert response.json()["code"] == "M999"

    async def test_patch_code_to_existing_value_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school_a, school_b] = await _seed(
            db_session,
            _make_school(code="M134"),
            _make_school(code="K001", name="Another School"),
        )
        response = await auth_client.patch(
            f"/schools/{school_a.id}", json={"code": "K001"}
        )
        assert response.status_code == 422

    async def test_patch_code_to_own_value_does_not_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school] = await _seed(db_session, _make_school(code="M134"))
        response = await auth_client.patch(
            f"/schools/{school.id}", json={"code": "M134"}
        )
        assert response.status_code == 200

    async def test_invalid_state_too_short_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school] = await _seed(db_session, _make_school())
        response = await auth_client.patch(
            f"/schools/{school.id}", json={"state": "N"}
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /schools/{school_id}/connections
# ---------------------------------------------------------------------------


class TestGetSchoolConnections:
    async def test_clean_entity_returns_zero_counts(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school] = await _seed(db_session, _make_school())
        response = await auth_client.get(f"/schools/{school.id}/connections")
        assert response.status_code == 200
        assert response.json()["project_school_links"] == 0

    async def test_counts_reflect_existing_references(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.projects.models import Project

        [school] = await _seed(db_session, _make_school())
        project = Project(name="Conn Project", project_number="26-CONN-S001")
        project.schools = [school]
        db_session.add(project)
        await db_session.flush()

        response = await auth_client.get(f"/schools/{school.id}/connections")
        assert response.status_code == 200
        assert response.json()["project_school_links"] == 1

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/schools/9999/connections")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /schools/{school_id}
# ---------------------------------------------------------------------------


class TestDeleteSchool:
    async def test_clean_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [school] = await _seed(db_session, _make_school())
        response = await auth_client.delete(f"/schools/{school.id}")
        assert response.status_code == 204

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/schools/9999")
        assert response.status_code == 404

    async def test_blocked_by_project_link_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.projects.models import Project

        [school] = await _seed(db_session, _make_school())
        project = Project(name="Del Project", project_number="26-DEL-S001")
        project.schools = [school]
        db_session.add(project)
        await db_session.flush()

        response = await auth_client.delete(f"/schools/{school.id}")
        assert response.status_code == 409
        assert "project_school_links" in response.json()["detail"]["blocked_by"]
