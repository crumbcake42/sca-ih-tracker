"""
Integration tests for deliverable WA code trigger endpoints.

GET    /deliverables/{id}/triggers
POST   /deliverables/{id}/triggers
DELETE /deliverables/{id}/triggers/{wa_code_id}
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WACodeLevel
from app.deliverables.models import Deliverable, DeliverableWACodeTrigger
from app.wa_codes.models import WACode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_deliverable(
    db: AsyncSession,
    name: str = "Test Report",
    level: WACodeLevel = WACodeLevel.PROJECT,
) -> Deliverable:
    d = Deliverable(name=name, level=level)
    db.add(d)
    await db.flush()
    return d


async def _seed_wa_code(
    db: AsyncSession,
    code: str = "P-001",
    level: WACodeLevel = WACodeLevel.PROJECT,
) -> WACode:
    wac = WACode(code=code, description=f"Description for {code}", level=level)
    db.add(wac)
    await db.flush()
    return wac


# ---------------------------------------------------------------------------
# GET /deliverables/{id}/triggers
# ---------------------------------------------------------------------------


class TestListTriggers:
    async def test_list_returns_200(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        d = await _seed_deliverable(db_session)
        wac = await _seed_wa_code(db_session)
        db_session.add(DeliverableWACodeTrigger(deliverable_id=d.id, wa_code_id=wac.id))
        await db_session.flush()

        response = await auth_client.get(f"/deliverables/{d.id}/triggers")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["wa_code_id"] == wac.id

    async def test_empty_list(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        d = await _seed_deliverable(db_session)
        response = await auth_client.get(f"/deliverables/{d.id}/triggers")
        assert response.status_code == 200
        assert response.json() == []

    async def test_missing_deliverable_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/deliverables/9999/triggers")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /deliverables/{id}/triggers
# ---------------------------------------------------------------------------


class TestAddTrigger:
    async def test_add_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        d = await _seed_deliverable(db_session)
        wac = await _seed_wa_code(db_session)

        response = await auth_client.post(
            f"/deliverables/{d.id}/triggers",
            json={"wa_code_id": wac.id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["deliverable_id"] == d.id
        assert data["wa_code_id"] == wac.id

    async def test_missing_wa_code_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        d = await _seed_deliverable(db_session)
        response = await auth_client.post(
            f"/deliverables/{d.id}/triggers",
            json={"wa_code_id": 9999},
        )
        assert response.status_code == 404

    async def test_missing_deliverable_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wac = await _seed_wa_code(db_session)
        response = await auth_client.post(
            "/deliverables/9999/triggers",
            json={"wa_code_id": wac.id},
        )
        assert response.status_code == 404

    async def test_duplicate_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        d = await _seed_deliverable(db_session)
        wac = await _seed_wa_code(db_session)
        db_session.add(DeliverableWACodeTrigger(deliverable_id=d.id, wa_code_id=wac.id))
        await db_session.flush()

        response = await auth_client.post(
            f"/deliverables/{d.id}/triggers",
            json={"wa_code_id": wac.id},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /deliverables/{id}/triggers/{wa_code_id}
# ---------------------------------------------------------------------------


class TestDeleteTrigger:
    async def test_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        d = await _seed_deliverable(db_session)
        wac = await _seed_wa_code(db_session)
        db_session.add(DeliverableWACodeTrigger(deliverable_id=d.id, wa_code_id=wac.id))
        await db_session.flush()

        response = await auth_client.delete(f"/deliverables/{d.id}/triggers/{wac.id}")
        assert response.status_code == 204

        follow_up = await auth_client.get(f"/deliverables/{d.id}/triggers")
        assert follow_up.json() == []

    async def test_missing_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        d = await _seed_deliverable(db_session)
        response = await auth_client.delete(f"/deliverables/{d.id}/triggers/9999")
        assert response.status_code == 404
