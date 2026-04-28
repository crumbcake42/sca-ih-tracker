"""
Integration tests for the deliverables base router.

GET    /deliverables/{deliverable_id}/connections
DELETE /deliverables/{deliverable_id}
"""

from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WACodeLevel
from app.deliverables.models import Deliverable, DeliverableWACodeTrigger
from app.wa_codes.models import WACode


def _make_deliverable(**overrides) -> Deliverable:
    defaults = dict(name="Air Clearance Report", level=WACodeLevel.PROJECT)
    return Deliverable(**{**defaults, **overrides})


def _make_wa_code(**overrides) -> WACode:
    defaults = dict(
        code="WA-D01",
        description="Asbestos abatement project",
        level=WACodeLevel.PROJECT,
        default_fee=Decimal("100.00"),
    )
    return WACode(**{**defaults, **overrides})


async def _seed(db: AsyncSession, *objs) -> list:
    for obj in objs:
        db.add(obj)
    await db.flush()
    return list(objs)


# ---------------------------------------------------------------------------
# GET /deliverables/{deliverable_id}/connections
# ---------------------------------------------------------------------------


class TestGetDeliverableConnections:
    async def test_clean_entity_returns_zero_counts(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [deliverable] = await _seed(db_session, _make_deliverable())
        response = await auth_client.get(f"/deliverables/{deliverable.id}/connections")
        assert response.status_code == 200
        data = response.json()
        assert data["project_deliverables"] == 0
        assert data["project_building_deliverables"] == 0
        assert data["deliverable_wa_code_triggers"] == 0

    async def test_counts_reflect_existing_references(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [deliverable, wa_code] = await _seed(
            db_session, _make_deliverable(), _make_wa_code()
        )
        db_session.add(DeliverableWACodeTrigger(deliverable_id=deliverable.id, wa_code_id=wa_code.id))
        await db_session.flush()

        response = await auth_client.get(f"/deliverables/{deliverable.id}/connections")
        assert response.status_code == 200
        assert response.json()["deliverable_wa_code_triggers"] == 1

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/deliverables/9999/connections")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /deliverables/{deliverable_id}
# ---------------------------------------------------------------------------


class TestDeleteDeliverable:
    async def test_clean_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [deliverable] = await _seed(db_session, _make_deliverable())
        response = await auth_client.delete(f"/deliverables/{deliverable.id}")
        assert response.status_code == 204

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/deliverables/9999")
        assert response.status_code == 404

    async def test_blocked_by_wa_code_trigger_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [deliverable, wa_code] = await _seed(
            db_session, _make_deliverable(), _make_wa_code()
        )
        db_session.add(DeliverableWACodeTrigger(deliverable_id=deliverable.id, wa_code_id=wa_code.id))
        await db_session.flush()

        response = await auth_client.delete(f"/deliverables/{deliverable.id}")
        assert response.status_code == 409
        assert "deliverable_wa_code_triggers" in response.json()["detail"]["blocked_by"]


# ---------------------------------------------------------------------------
# POST /deliverables/
# ---------------------------------------------------------------------------


class TestCreateDeliverable:
    async def test_create_returns_201_and_payload(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        payload = {"name": "Final Air Clearance", "description": "Required at close", "level": "project"}
        response = await auth_client.post("/deliverables/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Final Air Clearance"
        assert data["description"] == "Required at close"
        assert data["level"] == WACodeLevel.PROJECT
        assert "id" in data

    async def test_create_duplicate_name_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_deliverable(name="Bulk Sampling Report"))
        payload = {"name": "Bulk Sampling Report", "level": WACodeLevel.PROJECT}
        response = await auth_client.post("/deliverables/", json=payload)
        assert response.status_code == 422
        assert "already exists" in response.json()["detail"]


# ---------------------------------------------------------------------------
# PATCH /deliverables/{deliverable_id}
# ---------------------------------------------------------------------------


class TestUpdateDeliverable:
    async def test_patch_name_only_leaves_other_fields_unchanged(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [deliverable] = await _seed(
            db_session, _make_deliverable(name="Old Name", description="Keep this", level=WACodeLevel.PROJECT)
        )
        response = await auth_client.patch(
            f"/deliverables/{deliverable.id}", json={"name": "New Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "Keep this"
        assert data["level"] == WACodeLevel.PROJECT

    async def test_patch_unknown_id_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch("/deliverables/9999", json={"name": "X"})
        assert response.status_code == 404

    async def test_patch_immutable_level_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [deliverable] = await _seed(db_session, _make_deliverable(level=WACodeLevel.PROJECT))
        response = await auth_client.patch(
            f"/deliverables/{deliverable.id}", json={"level": WACodeLevel.BUILDING}
        )
        assert response.status_code == 422
        assert "level cannot be changed" in response.json()["detail"]

    async def test_patch_dup_name_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [first, second] = await _seed(
            db_session,
            _make_deliverable(name="First Report"),
            _make_deliverable(name="Second Report"),
        )
        response = await auth_client.patch(
            f"/deliverables/{second.id}", json={"name": "First Report"}
        )
        assert response.status_code == 422
        assert "already exists" in response.json()["detail"]

    async def test_patch_same_name_does_not_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [deliverable] = await _seed(db_session, _make_deliverable(name="Stable Name"))
        response = await auth_client.patch(
            f"/deliverables/{deliverable.id}", json={"name": "Stable Name"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Stable Name"
