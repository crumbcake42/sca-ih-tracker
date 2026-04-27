"""
Protocol contract tests for ContractorPaymentRecord.

Verifies that the ORM model satisfies the ProjectRequirement protocol structurally
and that class-level attributes match the required values.
"""

from datetime import datetime

from app.common.enums import CPRStageStatus
from app.cprs.models import ContractorPaymentRecord
from app.common.requirements import ManualTerminalMixin, ProjectRequirement


def _make_record(**overrides) -> ContractorPaymentRecord:
    defaults = dict(
        project_id=1,
        contractor_id=10,
        is_required=True,
    )
    defaults.update(overrides)
    return ContractorPaymentRecord(**defaults)


class TestContractorPaymentRecordProtocol:
    def test_instance_satisfies_protocol(self):
        record = _make_record()
        assert isinstance(record, ProjectRequirement)

    def test_requirement_type_is_correct(self):
        assert ContractorPaymentRecord.requirement_type == "contractor_payment_record"

    def test_is_dismissable_is_true(self):
        assert ContractorPaymentRecord.is_dismissable is True

    def test_has_manual_terminals_is_true(self):
        assert ContractorPaymentRecord.has_manual_terminals is True

    def test_inherits_manual_terminal_mixin(self):
        assert issubclass(ContractorPaymentRecord, ManualTerminalMixin)

    def test_is_fulfilled_false_when_rfp_not_saved(self):
        record = _make_record(rfp_saved_at=None)
        assert record.is_fulfilled() is False

    def test_is_fulfilled_true_when_rfp_saved(self):
        record = _make_record(rfp_saved_at=datetime(2025, 12, 1))
        assert record.is_fulfilled() is True

    def test_is_dismissed_reflects_dismissed_at(self):
        undismissed = _make_record()
        dismissed = _make_record(dismissed_at=datetime(2025, 12, 1))
        assert undismissed.is_dismissed is False
        assert dismissed.is_dismissed is True

    def test_requirement_key_is_contractor_id_string(self):
        record = _make_record(contractor_id=42)
        assert record.requirement_key == "42"

    def test_label_uses_contractor_relationship_when_loaded(self):
        from app.contractors.models import Contractor

        record = _make_record()
        record.contractor = Contractor(name="ACME Corp")
        assert record.label == "CPR — ACME Corp"

    def test_label_fallback_when_contractor_not_loaded(self):
        record = _make_record(contractor_id=7)
        record.contractor = None
        assert record.label == "CPR — Contractor #7"

    def test_stage_status_fields_default_to_none(self):
        record = _make_record()
        assert record.rfa_submitted_at is None
        assert record.rfa_internal_status is None
        assert record.rfa_sca_status is None
        assert record.rfp_submitted_at is None
        assert record.rfp_internal_status is None
        assert record.rfp_saved_at is None

    def test_cpr_stage_status_values(self):
        record = _make_record()
        record.rfa_internal_status = CPRStageStatus.APPROVED
        assert record.rfa_internal_status == CPRStageStatus.APPROVED
        assert record.rfa_internal_status == "approved"
