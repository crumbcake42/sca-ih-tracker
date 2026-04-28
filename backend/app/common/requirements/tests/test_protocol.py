"""
Contract tests for the ProjectRequirement protocol, registry, and mixins.
No database required — all assertions are structural/behavioural.
"""

from unittest.mock import MagicMock

import pytest

from app.common.enums import SCADeliverableStatus
from app.common.requirements import (
    DismissibleMixin,
    ManualTerminalMixin,
    ProjectRequirement,
    RequirementTypeRegistry,
)
from app.deliverables.requirement_adapter import (
    BuildingDeliverableRequirementAdapter,
    DeliverableRequirementAdapter,
)

# ---------------------------------------------------------------------------
# validate_template_params: deliverable adapters
# ---------------------------------------------------------------------------


class TestDeliverableAdapterValidateTemplateParams:
    def test_empty_params_accepted(self):
        DeliverableRequirementAdapter.validate_template_params({})

    def test_any_params_raise(self):
        with pytest.raises(ValueError, match="deliverable"):
            DeliverableRequirementAdapter.validate_template_params({"x": 1})


class TestBuildingDeliverableAdapterValidateTemplateParams:
    def test_empty_params_accepted(self):
        BuildingDeliverableRequirementAdapter.validate_template_params({})

    def test_any_params_raise(self):
        with pytest.raises(ValueError, match="building_deliverable"):
            BuildingDeliverableRequirementAdapter.validate_template_params({"x": 1})


# ---------------------------------------------------------------------------
# Protocol: runtime isinstance checks
# ---------------------------------------------------------------------------


class TestProjectRequirementProtocol:
    def _make_deliverable_adapter(self) -> DeliverableRequirementAdapter:
        row = MagicMock()
        row.project_id = 1
        row.deliverable_id = 2
        row.sca_status = SCADeliverableStatus.PENDING_WA
        deliv = MagicMock()
        deliv.name = "Test Report"
        return DeliverableRequirementAdapter(row, deliv)

    def _make_building_adapter(self) -> BuildingDeliverableRequirementAdapter:
        row = MagicMock()
        row.project_id = 1
        row.deliverable_id = 2
        row.school_id = 3
        row.sca_status = SCADeliverableStatus.OUTSTANDING
        deliv = MagicMock()
        deliv.name = "Building Report"
        return BuildingDeliverableRequirementAdapter(row, deliv)

    def test_deliverable_adapter_satisfies_protocol(self):
        adapter = self._make_deliverable_adapter()
        assert isinstance(adapter, ProjectRequirement)

    def test_building_deliverable_adapter_satisfies_protocol(self):
        adapter = self._make_building_adapter()
        assert isinstance(adapter, ProjectRequirement)

    def test_deliverable_adapter_properties(self):
        adapter = self._make_deliverable_adapter()
        assert adapter.project_id == 1
        assert adapter.requirement_type == "deliverable"
        assert adapter.label == "Test Report"
        assert adapter.is_dismissable is False
        assert adapter.is_dismissed is False

    def test_fulfilled_when_sca_status_is_manual_terminal(self):
        row = MagicMock()
        row.project_id = 1
        row.deliverable_id = 5
        row.sca_status = SCADeliverableStatus.APPROVED
        deliv = MagicMock()
        deliv.name = "Approved Report"
        adapter = DeliverableRequirementAdapter(row, deliv)
        assert adapter.is_fulfilled() is True

    def test_unfulfilled_when_sca_status_is_derivable(self):
        for status in (
            SCADeliverableStatus.PENDING_WA,
            SCADeliverableStatus.PENDING_RFA,
            SCADeliverableStatus.OUTSTANDING,
        ):
            row = MagicMock()
            row.project_id = 1
            row.deliverable_id = 5
            row.sca_status = status
            deliv = MagicMock()
            deliv.name = "Report"
            adapter = DeliverableRequirementAdapter(row, deliv)
            assert adapter.is_fulfilled() is False, f"Expected unfulfilled for {status}"


# ---------------------------------------------------------------------------
# Registry: duplicate-registration error
# ---------------------------------------------------------------------------


class TestRequirementTypeRegistry:
    def test_duplicate_registration_raises(self):
        fresh = RequirementTypeRegistry()

        class Foo:
            pass

        class Bar:
            pass

        fresh.register("foo", Foo)
        with pytest.raises(ValueError, match="already registered"):
            fresh.register("foo", Bar)

    def test_get_unknown_type_raises(self):
        fresh = RequirementTypeRegistry()
        with pytest.raises(KeyError, match="Unknown requirement type"):
            fresh.get("nonexistent")

    def test_all_handlers_returns_registered_classes(self):
        fresh = RequirementTypeRegistry()

        class A:
            pass

        class B:
            pass

        fresh.register("a", A)
        fresh.register("b", B)
        assert set(fresh.all_handlers()) == {A, B}

    def test_clear_empties_registry(self):
        fresh = RequirementTypeRegistry()

        class C:
            pass

        fresh.register("c", C)
        fresh.clear()
        assert list(fresh.all_handlers()) == []


# ---------------------------------------------------------------------------
# DismissibleMixin: column annotations present
# ---------------------------------------------------------------------------


class TestDismissibleMixin:
    def test_mixin_declares_three_columns(self):
        annotations = DismissibleMixin.__annotations__
        assert "dismissal_reason" in annotations
        assert "dismissed_by_id" in annotations
        assert "dismissed_at" in annotations


# ---------------------------------------------------------------------------
# ManualTerminalMixin: marker attribute
# ---------------------------------------------------------------------------


class TestManualTerminalMixin:
    def test_has_manual_terminals_flag(self):
        assert ManualTerminalMixin.has_manual_terminals is True

    def test_subclass_inherits_flag(self):
        class CPRHandler(ManualTerminalMixin):
            pass

        assert CPRHandler.has_manual_terminals is True
