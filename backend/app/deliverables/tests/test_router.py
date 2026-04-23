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
