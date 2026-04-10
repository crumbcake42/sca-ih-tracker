"""
Unit tests for app/common/formatters.py

No database or fixtures required — these are pure functions. If a test here
fails, the bug is in the formatter itself, not in a schema or a route.
"""

from app.common.formatters import format_phone_number


class TestFormatPhoneNumber:
    def test_bare_digits(self):
        assert format_phone_number("3471234567") == "(347) 123-4567"

    def test_dashes_stripped(self):
        assert format_phone_number("347-123-4567") == "(347) 123-4567"

    def test_dots_stripped(self):
        assert format_phone_number("347.123.4567") == "(347) 123-4567"

    def test_already_formatted_roundtrips(self):
        # If someone passes a correctly formatted string it should come back unchanged.
        assert format_phone_number("(347) 123-4567") == "(347) 123-4567"

    def test_wrong_length_passes_through_raw(self):
        # 9 digits — the formatter intentionally returns the raw value so the
        # downstream Pydantic regex can emit a useful error message.
        assert format_phone_number("123456789") == "123456789"

    def test_non_string_passes_through(self):
        # Pydantic BeforeValidator may pass None before the optional check runs.
        assert format_phone_number(None) is None
        assert format_phone_number(42) == 42
