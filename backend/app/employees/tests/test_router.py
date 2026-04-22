from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.employees.models import Employee


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
        await _seed_employee(db_session, first_name="John", last_name="Smith")
        response = await auth_client.post("/employees/", json=_payload())
        assert response.status_code == 201
        assert response.json()["display_name"] == "John Smith 2"

    async def test_third_collision_gets_suffix_3(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_employee(db_session, first_name="John", last_name="Smith")
        await _seed_employee(
            db_session, first_name="John", last_name="Smith", display_name="John Smith 2"
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
        await _seed_employee(db_session, adp_id="ABC123456")
        response = await auth_client.post(
            "/employees/", json=_payload(adp_id="ABC123456")
        )
        assert response.status_code == 422

    async def test_duplicate_email_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_employee(db_session, email="dup@example.com")
        response = await auth_client.post(
            "/employees/", json=_payload(email="dup@example.com")
        )
        assert response.status_code == 422

    async def test_duplicate_explicit_display_name_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_employee(db_session, display_name="Taken Name")
        response = await auth_client.post(
            "/employees/", json=_payload(display_name="Taken Name")
        )
        assert response.status_code == 422

    async def test_bad_adp_id_length_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/employees/", json=_payload(adp_id="SHORT")
        )
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
        emp = await _seed_employee(db_session)
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
        emp = await _seed_employee(db_session, created_by_id=1)
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"first_name": "Janet"}
        )
        assert response.json()["created_by_id"] == 1

    async def test_self_update_adp_id_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session, adp_id="ABC123456")
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"adp_id": "ABC123456"}
        )
        assert response.status_code == 200

    async def test_self_update_email_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session, email="same@example.com")
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"email": "same@example.com"}
        )
        assert response.status_code == 200

    async def test_self_update_display_name_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session, display_name="MyName")
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"display_name": "MyName"}
        )
        assert response.status_code == 200

    async def test_clear_email_to_null(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session, email="clear@example.com")
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"email": None}
        )
        assert response.status_code == 200
        assert response.json()["email"] is None

    async def test_rename_display_name_to_nickname(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session)
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
        await _seed_employee(db_session, adp_id="OTHER1234")
        emp = await _seed_employee(
            db_session, first_name="Bob", last_name="Jones", display_name="Bob Jones"
        )
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"adp_id": "OTHER1234"}
        )
        assert response.status_code == 422

    async def test_duplicate_email_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_employee(db_session, email="taken@example.com")
        emp = await _seed_employee(
            db_session, first_name="Bob", last_name="Jones", display_name="Bob Jones"
        )
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"email": "taken@example.com"}
        )
        assert response.status_code == 422

    async def test_duplicate_display_name_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_employee(db_session, display_name="Taken Name")
        emp = await _seed_employee(
            db_session, first_name="Bob", last_name="Jones", display_name="Bob Jones"
        )
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"display_name": "Taken Name"}
        )
        assert response.status_code == 422


    async def test_bad_phone_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        emp = await _seed_employee(db_session)
        response = await auth_client.patch(
            f"/employees/{emp.id}", json={"phone": "555123666"}
        )
        assert response.status_code == 422
