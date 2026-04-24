"""
Unit tests for app/employees/schemas.py

Two distinct concerns live here:
  1. Field-level validation (phone formatting, adp_id pattern, email coercion)
  2. The end_after_start model_validator on EmployeeRoleBase

The DB-level overlap check (which requires a query) is tested separately in
test_roles.py. Keeping schema validation separate from DB validation means a
failing test points you to exactly one layer.
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.employees.schemas import EmployeeBase, EmployeeRoleCreate

# ---------------------------------------------------------------------------
# EmployeeBase — field validation
# ---------------------------------------------------------------------------


class TestEmployeeBasePhone:
    def test_raw_digits_formatted(self):
        emp = EmployeeBase(first_name="Jane", last_name="Doe", phone="3471234567")  # type: ignore
        assert emp.phone == "(347) 123-4567"

    def test_already_formatted_passes(self):
        emp = EmployeeBase(first_name="Jane", last_name="Doe", phone="(347) 123-4567")  # type: ignore
        assert emp.phone == "(347) 123-4567"

    def test_wrong_length_fails(self):
        # 9 digits: formatter passes it through, regex rejects it.
        with pytest.raises(ValidationError):
            EmployeeBase(first_name="Jane", last_name="Doe", phone="123456789")  # type: ignore

    def test_empty_phone_becomes_none(self):
        emp = EmployeeBase(first_name="Jane", last_name="Doe", phone="")  # type: ignore
        assert emp.phone is None


class TestEmployeeBaseAdpId:
    def test_valid_9_char_alphanumeric(self):
        emp = EmployeeBase(first_name="Jane", last_name="Doe", adp_id="ABC123456")  # type: ignore
        assert emp.adp_id == "ABC123456"

    def test_too_long_fails(self):
        with pytest.raises(ValidationError):
            EmployeeBase(first_name="Jane", last_name="Doe", adp_id="TOOLONG123")  # type: ignore

    def test_special_chars_fail(self):
        with pytest.raises(ValidationError):
            EmployeeBase(first_name="Jane", last_name="Doe", adp_id="ABC-12345")  # type: ignore

    def test_empty_becomes_none(self):
        emp = EmployeeBase(first_name="Jane", last_name="Doe", adp_id="")  # type: ignore
        assert emp.adp_id is None


class TestEmployeeBaseEmail:
    def test_valid_email_passes(self):
        emp = EmployeeBase(first_name="Jane", last_name="Doe", email="jane@example.com")  # type: ignore
        assert emp.email == "jane@example.com"

    def test_invalid_email_fails(self):
        with pytest.raises(ValidationError):
            EmployeeBase(first_name="Jane", last_name="Doe", email="not-an-email")  # type: ignore

    def test_empty_becomes_none(self):
        emp = EmployeeBase(first_name="Jane", last_name="Doe", email="")  # type: ignore
        assert emp.email is None


# ---------------------------------------------------------------------------
# EmployeeRoleCreate — end_after_start model_validator
# ---------------------------------------------------------------------------
# Note: this validator fires at schema parse time, before any DB interaction.
# The overlap check (two roles covering the same date range) lives in the
# router and requires a DB query — that's tested in test_roles.py.


def _make_role(start: str, end: str | None, rate: str = "25.00") -> EmployeeRoleCreate:
    return EmployeeRoleCreate(
        role_type_id=1,  # FK not validated at schema layer
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end) if end else None,
        hourly_rate=Decimal(rate),
    )


class TestEmployeeRoleCreateDates:
    def test_open_ended_role_valid(self):
        role = _make_role("2024-01-01", None)
        assert role.end_date is None

    def test_end_after_start_valid(self):
        role = _make_role("2024-01-01", "2024-06-01")
        assert role.end_date == date(2024, 6, 1)

    def test_end_equal_to_start_fails(self):
        # The validator uses <=, so same-day end is explicitly disallowed.
        with pytest.raises(ValidationError, match="end_date must be after start_date"):
            _make_role("2024-01-01", "2024-01-01")

    def test_end_before_start_fails(self):
        with pytest.raises(ValidationError, match="end_date must be after start_date"):
            _make_role("2024-06-01", "2024-01-01")

    def test_negative_rate_fails(self):
        with pytest.raises(ValidationError):
            _make_role("2024-01-01", None, rate="-5.00")
