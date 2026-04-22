"""
Integration tests for the wa_codes router POST/PATCH endpoints.

The factory-generated list/get and the hand-written GET /{identifier} are
covered by the schools test suite (same factory). These tests focus on the
write endpoints unique to wa_codes — the duplicate-code/description guards
and the level-immutability guard.
"""

from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WACodeLevel
from app.wa_codes.models import WACode


def _make_wa_code(**overrides) -> WACode:
    defaults = dict(
        code="WA-001",
        description="Asbestos abatement project",
        level=WACodeLevel.PROJECT,
        default_fee=Decimal("100.00"),
    )
    return WACode(**{**defaults, **overrides})


async def _seed(db: AsyncSession, *wa_codes: WACode) -> list[WACode]:
    for wc in wa_codes:
        db.add(wc)
    await db.flush()
    return list(wa_codes)


_VALID_PAYLOAD = dict(
    code="WA-100",
    description="Lead inspection project",
    level="project",
    default_fee="250.00",
)


# ---------------------------------------------------------------------------
# POST /wa-codes/
# ---------------------------------------------------------------------------


class TestCreateWACode:
    async def test_happy_path_returns_201(self, auth_client: AsyncClient):
        response = await auth_client.post("/wa-codes/", json=_VALID_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "WA-100"
        assert data["level"] == "project"
        assert "id" in data

    async def test_created_by_id_stamped(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        response = await auth_client.post("/wa-codes/", json=_VALID_PAYLOAD)
        assert response.status_code == 201
        wa_code_id = response.json()["id"]
        result = await db_session.get(WACode, wa_code_id)
        assert result and result.created_by_id is not None

    async def test_default_fee_optional(self, auth_client: AsyncClient):
        payload = {**_VALID_PAYLOAD}
        payload.pop("default_fee")
        response = await auth_client.post("/wa-codes/", json=payload)
        assert response.status_code == 201
        assert response.json()["default_fee"] is None

    async def test_duplicate_code_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_wa_code(code="WA-100"))
        response = await auth_client.post("/wa-codes/", json=_VALID_PAYLOAD)
        assert response.status_code == 422

    async def test_duplicate_description_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_wa_code(code="WA-OTHER", description="Lead inspection project"),
        )
        response = await auth_client.post("/wa-codes/", json=_VALID_PAYLOAD)
        assert response.status_code == 422

    async def test_negative_fee_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/wa-codes/", json={**_VALID_PAYLOAD, "default_fee": "-1.00"}
        )
        assert response.status_code == 422

    async def test_invalid_level_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/wa-codes/", json={**_VALID_PAYLOAD, "level": "not-a-level"}
        )
        assert response.status_code == 422

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.post("/wa-codes/", json=_VALID_PAYLOAD)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /wa-codes/{id}
# ---------------------------------------------------------------------------


class TestUpdateWACode:
    async def test_partial_update_description(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(db_session, _make_wa_code())
        response = await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"description": "Updated description"}
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"
        assert response.json()["code"] == "WA-001"

    async def test_updated_by_id_stamped(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(db_session, _make_wa_code())
        await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"description": "Updated"}
        )
        await db_session.refresh(wa_code)
        assert wa_code.updated_by_id is not None

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(
            "/wa-codes/9999", json={"description": "x"}
        )
        assert response.status_code == 404

    async def test_patch_code_to_new_value(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(db_session, _make_wa_code(code="WA-001"))
        response = await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"code": "WA-999"}
        )
        assert response.status_code == 200
        assert response.json()["code"] == "WA-999"

    async def test_patch_code_to_existing_value_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [a, _b] = await _seed(
            db_session,
            _make_wa_code(code="WA-001", description="A"),
            _make_wa_code(code="WA-002", description="B"),
        )
        response = await auth_client.patch(
            f"/wa-codes/{a.id}", json={"code": "WA-002"}
        )
        assert response.status_code == 422

    async def test_patch_code_to_own_value_does_not_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(db_session, _make_wa_code(code="WA-001"))
        response = await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"code": "WA-001"}
        )
        assert response.status_code == 200

    async def test_patch_description_to_existing_value_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [a, _b] = await _seed(
            db_session,
            _make_wa_code(code="WA-001", description="A"),
            _make_wa_code(code="WA-002", description="B"),
        )
        response = await auth_client.patch(
            f"/wa-codes/{a.id}", json={"description": "B"}
        )
        assert response.status_code == 422

    async def test_patch_description_to_own_value_does_not_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(db_session, _make_wa_code(description="Same"))
        response = await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"description": "Same"}
        )
        assert response.status_code == 200

    async def test_patch_level_to_same_value_allowed(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(db_session, _make_wa_code(level=WACodeLevel.PROJECT))
        response = await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"level": "project"}
        )
        assert response.status_code == 200

    async def test_patch_level_to_different_value_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(db_session, _make_wa_code(level=WACodeLevel.PROJECT))
        response = await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"level": "building"}
        )
        assert response.status_code == 422

    async def test_patch_default_fee_to_null(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(
            db_session, _make_wa_code(default_fee=Decimal("50.00"))
        )
        response = await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"default_fee": None}
        )
        assert response.status_code == 200
        assert response.json()["default_fee"] is None

    async def test_negative_fee_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [wa_code] = await _seed(db_session, _make_wa_code())
        response = await auth_client.patch(
            f"/wa-codes/{wa_code.id}", json={"default_fee": "-5.00"}
        )
        assert response.status_code == 422
