from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.seeds import seed_employee


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload(**overrides) -> dict:
    defaults = dict(first_name="John", last_name="Smith")
    return {**defaults, **overrides}


# ---------------------------------------------------------------------------
# POST /employees/
# ---------------------------------------------------------------------------


class TestCreateEmployee:
    async def test_minimal_returns_201_with_auto_display_name(
        self, auth_client: AsyncClient
    ):
        response = await auth_client.post("/employees/", json=_payload())
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Smith"
        assert data["display_name"] == "John Smith"
        assert data["id"] is not None
        assert data["created_by_id"] is not None

    async def test_auto_dedup_display_name(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await seed_employee(db_session, first_name="John", last_name="Smith")
        response = await auth_client.post("/employees/", json=_payload())
        assert response.status_code == 201
        assert response.json()["display_name"] == "John Smith 2"

    async def test_third_collision_gets_suffix_3(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await seed_employee(db_session, first_name="John", last_name="Smith")
        await seed_employee(
            db_session,
            first_name="John",
            last_name="Smith",
            display_name="John Smith 2",
        )
        response = await auth_client.post("/employees/", json=_payload())
        assert response.status_code == 201
        assert response.json()["display_name"] == "John Smith 3"

    async def test_explicit_display_name_is_used(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/employees/", json=_payload(display_name="JSmith")
        )
        assert response.status_code == 201
        assert response.json()["display_name"] == "JSmith"

    async def test_full_payload_round_trips(self, auth_client: AsyncClient):
        payload = _payload(
            display_name="Johnny",
            email="john@example.com",
            phone="(555) 123-4567",
            adp_id="ABC123456",
        )
        response = await auth_client.post("/employees/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "john@example.com"
        assert data["phone"] == "(555) 123-4567"
        assert data["adp_id"] == "ABC123456"
        assert data["display_name"] == "Johnny"

    async def test_duplicate_adp_id_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await seed_employee(db_session, adp_id="ABC123456")
        response = await auth_client.post(
            "/employees/", json=_payload(adp_id="ABC123456")
        )
        assert response.status_code == 422

    async def test_duplicate_email_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await seed_employee(db_session, email="dup@example.com")
        response = await auth_client.post(
            "/employees/", json=_payload(email="dup@example.com")
        )
        assert response.status_code == 422

    async def test_duplicate_explicit_display_name_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await seed_employee(db_session, display_name="Taken Name")
        response = await auth_client.post(
            "/employees/", json=_payload(display_name="Taken Name")
        )
        assert response.status_code == 422

    async def test_bad_adp_id_length_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post("/employees/", json=_payload(adp_id="SHORT"))
        assert response.status_code == 422

    async def test_missing_first_name_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post("/employees/", json={"last_name": "Smith"})
        assert response.status_code == 422

    async def test_missing_last_name_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post("/employees/", json={"first_name": "John"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /employees/{id}
# ---------------------------------------------------------------------------


class TestUpdateEmployee:
    async def test_partial_update_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session)
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"first_name": "Janet"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Janet"
        assert data["last_name"] == "Doe"
        assert data["updated_by_id"] is not None

    async def test_created_by_id_unchanged_after_patch(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session, created_by_id=1)
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"first_name": "Janet"}
        )
        assert response.json()["created_by_id"] == 1

    async def test_self_update_adp_id_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session, adp_id="ABC123456")
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"adp_id": "ABC123456"}
        )
        assert response.status_code == 200

    async def test_self_update_email_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session, email="same@example.com")
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"email": "same@example.com"}
        )
        assert response.status_code == 200

    async def test_self_update_display_name_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session, display_name="MyName")
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"display_name": "MyName"}
        )
        assert response.status_code == 200

    async def test_clear_email_to_null(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session, email="clear@example.com")
        response = await auth_client.patch(f"/employees/{emp.id}", json={"email": None})
        assert response.status_code == 200
        assert response.json()["email"] is None

    async def test_rename_display_name_to_nickname(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session)
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"display_name": "JDoe"}
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "JDoe"

    async def test_unknown_id_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch("/employees/9999", json={"first_name": "X"})
        assert response.status_code == 404

    async def test_duplicate_adp_id_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await seed_employee(db_session, adp_id="OTHER1234")
        emp = await seed_employee(
            db_session, first_name="Bob", last_name="Jones", display_name="Bob Jones"
        )
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"adp_id": "OTHER1234"}
        )
        assert response.status_code == 422

    async def test_duplicate_email_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await seed_employee(db_session, email="taken@example.com")
        emp = await seed_employee(
            db_session, first_name="Bob", last_name="Jones", display_name="Bob Jones"
        )
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"email": "taken@example.com"}
        )
        assert response.status_code == 422

    async def test_duplicate_display_name_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await seed_employee(db_session, display_name="Taken Name")
        emp = await seed_employee(
            db_session, first_name="Bob", last_name="Jones", display_name="Bob Jones"
        )
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"display_name": "Taken Name"}
        )
        assert response.status_code == 422

    async def test_bad_phone_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session)
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"phone": "555123666"}
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /employees/{employee_id}/connections
# ---------------------------------------------------------------------------


class TestGetEmployeeConnections:
    async def test_clean_entity_returns_zero_counts(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session)
        response = await auth_client.get(f"/employees/{emp.id}/connections")
        assert response.status_code == 200
        data = response.json()
        assert data["time_entries"] == 0
        assert data["sample_batch_inspectors"] == 0

    async def test_counts_reflect_existing_references(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.lab_results.models import SampleBatch, SampleBatchInspector, SampleType

        emp = await seed_employee(db_session)

        sample_type = SampleType(name="Air Asbestos Conn")
        db_session.add(sample_type)
        await db_session.flush()

        from datetime import date

        batch = SampleBatch(
            sample_type_id=sample_type.id,
            batch_num="B-CONN-EMP-001",
            date_collected=date(2025, 1, 1),
        )
        db_session.add(batch)
        await db_session.flush()

        db_session.add(SampleBatchInspector(batch_id=batch.id, employee_id=emp.id))
        await db_session.flush()

        response = await auth_client.get(f"/employees/{emp.id}/connections")
        assert response.status_code == 200
        assert response.json()["sample_batch_inspectors"] == 1

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/employees/9999/connections")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /employees/{employee_id}
# ---------------------------------------------------------------------------


class TestDeleteEmployee:
    async def test_clean_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await seed_employee(db_session)
        response = await auth_client.delete(f"/employees/{emp.id}")
        assert response.status_code == 204

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/employees/9999")
        assert response.status_code == 404

    async def test_blocked_by_sample_batch_inspector_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.lab_results.models import SampleBatch, SampleBatchInspector, SampleType

        emp = await seed_employee(db_session)

        sample_type = SampleType(name="Air Asbestos Del")
        db_session.add(sample_type)
        await db_session.flush()

        from datetime import date

        batch = SampleBatch(
            sample_type_id=sample_type.id,
            batch_num="B-DEL-EMP-001",
            date_collected=date(2025, 1, 1),
        )
        db_session.add(batch)
        await db_session.flush()

        db_session.add(SampleBatchInspector(batch_id=batch.id, employee_id=emp.id))
        await db_session.flush()

        response = await auth_client.delete(f"/employees/{emp.id}")
        assert response.status_code == 409
        assert "sample_batch_inspectors" in response.json()["detail"]["blocked_by"]
