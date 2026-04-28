"""
Integration tests for POST/GET/DELETE /requirement-triggers/.

Registry validation (unknown requirement_type_name → 422) uses the registered
types from Session A ("deliverable", "building_deliverable") — no fake types
needed because the global registry is populated via app.main import.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.requirement_triggers.models import WACodeRequirementTrigger
from app.requirement_triggers.services import hash_template_params
from tests.seeds import seed_wa_code


def _trigger_payload(wa_code_id: int, **overrides) -> dict:
    defaults = dict(
        wa_code_id=wa_code_id,
        requirement_type_name="project_document",
        template_params={"document_type": "daily_log"},
    )
    return {**defaults, **overrides}


async def _seed_trigger(
    db: AsyncSession,
    wa_code_id: int,
    requirement_type_name: str = "deliverable",
    template_params: dict | None = None,
) -> WACodeRequirementTrigger:
    params = template_params or {}
    trigger = WACodeRequirementTrigger(
        wa_code_id=wa_code_id,
        requirement_type_name=requirement_type_name,
        template_params=params,
        template_params_hash=hash_template_params(params),
    )
    db.add(trigger)
    await db.flush()
    return trigger


# ---------------------------------------------------------------------------
# POST /requirement-triggers/
# ---------------------------------------------------------------------------


class TestCreateRequirementTrigger:
    async def test_happy_path_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        response = await auth_client.post(
            "/requirement-triggers/", json=_trigger_payload(wa_code.id)
        )
        assert response.status_code == 201
        data = response.json()
        assert data["wa_code_id"] == wa_code.id
        assert data["requirement_type_name"] == "project_document"
        assert data["template_params"] == {"document_type": "daily_log"}
        assert "id" in data

    async def test_created_by_id_stamped(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        response = await auth_client.post(
            "/requirement-triggers/", json=_trigger_payload(wa_code.id)
        )
        assert response.status_code == 201
        trigger = await db_session.get(WACodeRequirementTrigger, response.json()["id"])
        assert trigger and trigger.created_by_id is not None

    async def test_unknown_wa_code_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/requirement-triggers/", json=_trigger_payload(wa_code_id=99999)
        )
        assert response.status_code == 404

    async def test_unknown_requirement_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        response = await auth_client.post(
            "/requirement-triggers/",
            json=_trigger_payload(
                wa_code.id, requirement_type_name="not_a_real_type"
            ),
        )
        assert response.status_code == 422
        # Pydantic validates the Literal at the schema layer; detail is a list of error objects
        detail = response.json()["detail"]
        assert any("not_a_real_type" in str(err) for err in detail)

    async def test_duplicate_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        payload = _trigger_payload(wa_code.id)
        await auth_client.post("/requirement-triggers/", json=payload)
        response = await auth_client.post("/requirement-triggers/", json=payload)
        assert response.status_code == 409

    async def test_unauthenticated_returns_4xx(self, client: AsyncClient, db_session: AsyncSession):
        wa_code = await seed_wa_code(db_session)
        response = await client.post(
            "/requirement-triggers/", json=_trigger_payload(wa_code.id)
        )
        assert response.status_code in (401, 403)

    async def test_non_wa_code_handler_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        response = await auth_client.post(
            "/requirement-triggers/",
            json=_trigger_payload(
                wa_code.id,
                requirement_type_name="contractor_payment_record",
                template_params={},
            ),
        )
        assert response.status_code == 422
        assert "WA_CODE_ADDED" in response.json()["detail"]

    async def test_deliverable_handler_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        response = await auth_client.post(
            "/requirement-triggers/",
            json=_trigger_payload(
                wa_code.id,
                requirement_type_name="deliverable",
                template_params={},
            ),
        )
        assert response.status_code == 422

    async def test_invalid_document_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        response = await auth_client.post(
            "/requirement-triggers/",
            json=_trigger_payload(
                wa_code.id,
                template_params={"document_type": "safety_report"},
            ),
        )
        assert response.status_code == 422
        assert "safety_report" in response.json()["detail"]

    async def test_extra_template_params_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        response = await auth_client.post(
            "/requirement-triggers/",
            json=_trigger_payload(
                wa_code.id,
                template_params={"document_type": "daily_log", "extra": "field"},
            ),
        )
        assert response.status_code == 422

    async def test_missing_document_type_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        response = await auth_client.post(
            "/requirement-triggers/",
            json=_trigger_payload(wa_code.id, template_params={}),
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /requirement-triggers/
# ---------------------------------------------------------------------------


class TestListRequirementTriggers:
    async def test_returns_all_triggers_when_no_filter(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa1 = await seed_wa_code(db_session)
        wa2 = await seed_wa_code(db_session)
        await _seed_trigger(db_session, wa1.id)
        await _seed_trigger(db_session, wa2.id)

        response = await auth_client.get("/requirement-triggers/")
        assert response.status_code == 200
        ids = {r["wa_code_id"] for r in response.json()}
        assert wa1.id in ids and wa2.id in ids

    async def test_wa_code_id_filter(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa1 = await seed_wa_code(db_session)
        wa2 = await seed_wa_code(db_session)
        await _seed_trigger(db_session, wa1.id)
        await _seed_trigger(db_session, wa2.id)

        response = await auth_client.get(f"/requirement-triggers/?wa_code_id={wa1.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(r["wa_code_id"] == wa1.id for r in data)

    async def test_empty_result_for_unknown_wa_code_id(self, auth_client: AsyncClient):
        response = await auth_client.get("/requirement-triggers/?wa_code_id=99999")
        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# DELETE /requirement-triggers/{trigger_id}
# ---------------------------------------------------------------------------


class TestDeleteRequirementTrigger:
    async def test_happy_path_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        trigger = await _seed_trigger(db_session, wa_code.id)

        response = await auth_client.delete(f"/requirement-triggers/{trigger.id}")
        assert response.status_code == 204

        assert await db_session.get(WACodeRequirementTrigger, trigger.id) is None

    async def test_unknown_trigger_id_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/requirement-triggers/99999")
        assert response.status_code == 404

    async def test_unauthenticated_returns_4xx(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        wa_code = await seed_wa_code(db_session)
        trigger = await _seed_trigger(db_session, wa_code.id)
        response = await client.delete(f"/requirement-triggers/{trigger.id}")
        assert response.status_code in (401, 403)
