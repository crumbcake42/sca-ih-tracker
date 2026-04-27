"""
Model-level tests for WACodeRequirementTrigger.

Verifies the round-trip persistence, unique constraint enforcement, and
AuditMixin stamping. Cascade-on-WA-code-delete is defined at the DB level
(ondelete="CASCADE") and is not tested here because the in-memory SQLite
test engine does not enable PRAGMA foreign_keys by default.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.project_requirements.models import WACodeRequirementTrigger
from app.project_requirements.services import hash_template_params
from tests.seeds import seed_wa_code


class TestWACodeRequirementTriggerModel:
    async def test_round_trip_insert_and_select(self, db_session: AsyncSession):
        wa_code = await seed_wa_code(db_session)
        params = {"document_type": "SURVEY_REPORT"}
        trigger = WACodeRequirementTrigger(
            wa_code_id=wa_code.id,
            requirement_type_name="deliverable",
            template_params=params,
            template_params_hash=hash_template_params(params),
        )
        db_session.add(trigger)
        await db_session.flush()

        fetched = await db_session.get(WACodeRequirementTrigger, trigger.id)
        assert fetched is not None
        assert fetched.wa_code_id == wa_code.id
        assert fetched.requirement_type_name == "deliverable"
        assert fetched.template_params == params
        assert len(fetched.template_params_hash) == 64

    async def test_unique_constraint_rejects_duplicate(self, db_session: AsyncSession):
        wa_code = await seed_wa_code(db_session)
        params = {"x": 1}
        h = hash_template_params(params)

        t1 = WACodeRequirementTrigger(
            wa_code_id=wa_code.id,
            requirement_type_name="deliverable",
            template_params=params,
            template_params_hash=h,
        )
        db_session.add(t1)
        await db_session.flush()

        t2 = WACodeRequirementTrigger(
            wa_code_id=wa_code.id,
            requirement_type_name="deliverable",
            template_params=params,
            template_params_hash=h,
        )
        db_session.add(t2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_same_type_different_wa_codes_allowed(self, db_session: AsyncSession):
        wa1 = await seed_wa_code(db_session)
        wa2 = await seed_wa_code(db_session)
        params = {"x": 1}
        h = hash_template_params(params)

        for wa in (wa1, wa2):
            db_session.add(
                WACodeRequirementTrigger(
                    wa_code_id=wa.id,
                    requirement_type_name="deliverable",
                    template_params=params,
                    template_params_hash=h,
                )
            )
        await db_session.flush()

    async def test_same_wa_code_different_types_allowed(self, db_session: AsyncSession):
        wa_code = await seed_wa_code(db_session)
        params = {"x": 1}
        h = hash_template_params(params)

        for type_name in ("deliverable", "building_deliverable"):
            db_session.add(
                WACodeRequirementTrigger(
                    wa_code_id=wa_code.id,
                    requirement_type_name=type_name,
                    template_params=params,
                    template_params_hash=h,
                )
            )
        await db_session.flush()

    async def test_same_wa_code_same_type_different_params_allowed(self, db_session: AsyncSession):
        wa_code = await seed_wa_code(db_session)

        for params in ({"x": 1}, {"x": 2}):
            db_session.add(
                WACodeRequirementTrigger(
                    wa_code_id=wa_code.id,
                    requirement_type_name="deliverable",
                    template_params=params,
                    template_params_hash=hash_template_params(params),
                )
            )
        await db_session.flush()

    async def test_audit_timestamps_populated(self, db_session: AsyncSession):
        wa_code = await seed_wa_code(db_session)
        params = {}
        trigger = WACodeRequirementTrigger(
            wa_code_id=wa_code.id,
            requirement_type_name="deliverable",
            template_params=params,
            template_params_hash=hash_template_params(params),
        )
        db_session.add(trigger)
        await db_session.flush()

        fetched = await db_session.get(WACodeRequirementTrigger, trigger.id)
        assert fetched.created_at is not None
        assert fetched.updated_at is not None
