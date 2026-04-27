"""
Tests for dispatch_requirement_event().

Uses fresh RequirementTypeRegistry instances per test — never clears the global
registry (per README guidance). Monkeypatches services.registry so the dispatcher
sees the isolated test registry without touching the global.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.common.enums import RequirementEvent
from app.project_requirements.registry import RequirementTypeRegistry


class TestDispatchRequirementEvent:
    @pytest.fixture
    def fresh_registry(self):
        return RequirementTypeRegistry()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    async def test_subscribed_handler_is_called(self, fresh_registry, mock_db, monkeypatch):
        handle_event = AsyncMock()

        class FakeHandler:
            pass

        FakeHandler.handle_event = handle_event
        fresh_registry.register("fake", FakeHandler, events=[RequirementEvent.WA_CODE_ADDED])

        import app.project_requirements.services as svc
        monkeypatch.setattr(svc, "registry", fresh_registry)

        await svc.dispatch_requirement_event(
            project_id=1,
            event=RequirementEvent.WA_CODE_ADDED,
            payload={"wa_code_id": 99},
            db=mock_db,
        )

        handle_event.assert_awaited_once_with(
            1, RequirementEvent.WA_CODE_ADDED, {"wa_code_id": 99}, mock_db
        )

    async def test_unsubscribed_handler_is_not_called(self, fresh_registry, mock_db, monkeypatch):
        handle_event = AsyncMock()

        class FakeHandler:
            pass

        FakeHandler.handle_event = handle_event
        # Subscribed to WA_CODE_REMOVED, not WA_CODE_ADDED
        fresh_registry.register("fake", FakeHandler, events=[RequirementEvent.WA_CODE_REMOVED])

        import app.project_requirements.services as svc
        monkeypatch.setattr(svc, "registry", fresh_registry)

        await svc.dispatch_requirement_event(
            project_id=1,
            event=RequirementEvent.WA_CODE_ADDED,
            payload={},
            db=mock_db,
        )

        handle_event.assert_not_awaited()

    async def test_no_subscribers_is_a_noop(self, fresh_registry, mock_db, monkeypatch):
        import app.project_requirements.services as svc
        monkeypatch.setattr(svc, "registry", fresh_registry)

        # Should not raise even with no handlers registered
        await svc.dispatch_requirement_event(
            project_id=1,
            event=RequirementEvent.WA_CODE_ADDED,
            payload={},
            db=mock_db,
        )

    async def test_multiple_subscribers_all_called(self, fresh_registry, mock_db, monkeypatch):
        handle_a = AsyncMock()
        handle_b = AsyncMock()

        class HandlerA:
            pass

        class HandlerB:
            pass

        HandlerA.handle_event = handle_a
        HandlerB.handle_event = handle_b
        fresh_registry.register("type_a", HandlerA, events=[RequirementEvent.WA_CODE_ADDED])
        fresh_registry.register("type_b", HandlerB, events=[RequirementEvent.WA_CODE_ADDED])

        import app.project_requirements.services as svc
        monkeypatch.setattr(svc, "registry", fresh_registry)

        await svc.dispatch_requirement_event(
            project_id=5,
            event=RequirementEvent.WA_CODE_ADDED,
            payload={"wa_code_id": 7},
            db=mock_db,
        )

        handle_a.assert_awaited_once()
        handle_b.assert_awaited_once()

    async def test_raising_handler_propagates_exception(self, fresh_registry, mock_db, monkeypatch):
        class HandlerThatRaises:
            @classmethod
            async def handle_event(cls, project_id, event, payload, db):
                raise RuntimeError("handler failed")

        fresh_registry.register("bad", HandlerThatRaises, events=[RequirementEvent.WA_CODE_ADDED])

        import app.project_requirements.services as svc
        monkeypatch.setattr(svc, "registry", fresh_registry)

        with pytest.raises(RuntimeError, match="handler failed"):
            await svc.dispatch_requirement_event(
                project_id=1,
                event=RequirementEvent.WA_CODE_ADDED,
                payload={},
                db=mock_db,
            )
