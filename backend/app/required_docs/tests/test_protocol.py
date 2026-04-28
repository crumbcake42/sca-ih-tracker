"""
Protocol contract tests for ProjectDocumentRequirement.

Verifies that the ORM model satisfies the ProjectRequirement protocol structurally
and that class-level attributes match the required values.
"""

from datetime import date

import pytest

from app.common.enums import DocumentType
from app.common.requirements import ProjectRequirement
from app.required_docs.models import ProjectDocumentRequirement


def _make_req(**overrides) -> ProjectDocumentRequirement:
    defaults = dict(
        project_id=1,
        document_type=DocumentType.DAILY_LOG,
        is_required=True,
        is_saved=False,
        is_placeholder=False,
        employee_id=10,
        date=date(2025, 11, 30),
        school_id=5,
    )
    defaults.update(overrides)
    return ProjectDocumentRequirement(**defaults)


class TestProjectRequirementProtocol:
    def test_instance_satisfies_protocol(self):
        req = _make_req()
        assert isinstance(req, ProjectRequirement)

    def test_requirement_type_is_project_document(self):
        assert ProjectDocumentRequirement.requirement_type == "project_document"

    def test_is_dismissable_is_true(self):
        assert ProjectDocumentRequirement.is_dismissable is True

    def test_is_fulfilled_reflects_is_saved(self):
        unsaved = _make_req(is_saved=False)
        saved = _make_req(is_saved=True)
        assert unsaved.is_fulfilled is False
        assert saved.is_fulfilled is True

    def test_is_dismissed_reflects_dismissed_at(self):
        from datetime import datetime

        undismissed = _make_req()
        dismissed = _make_req()
        dismissed.dismissed_at = datetime(2025, 12, 1)
        assert undismissed.is_dismissed is False
        assert dismissed.is_dismissed is True

    def test_label_daily_log_includes_date(self):
        req = _make_req(date=date(2025, 11, 30))
        assert "Daily Log" in req.label
        assert "2025-11-30" in req.label

    def test_label_daily_log_pending_when_no_date(self):
        req = _make_req(date=None)
        assert "pending" in req.label

    def test_label_reoccupancy_letter(self):
        req = _make_req(document_type=DocumentType.REOCCUPANCY_LETTER, employee_id=None, date=None, school_id=None)
        assert req.label == "Re-Occupancy Letter"

    def test_label_minor_letter(self):
        req = _make_req(document_type=DocumentType.MINOR_LETTER, employee_id=None, date=None, school_id=None)
        assert req.label == "Minor Letter"
