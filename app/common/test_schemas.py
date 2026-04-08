"""
Unit tests for app/common/schemas.py

Tests the OptionalField / empty_to_none behavior in isolation so that if
something breaks here we don't have to dig through employee or school schema
tests to find the root cause.
"""

import pytest
from pydantic import BaseModel, ValidationError
from app.common.schemas import OptionalField


class _Model(BaseModel):
    val: OptionalField[str] = None  # type: ignore[type-arg]


class TestOptionalField:
    def test_empty_string_becomes_none(self):
        assert _Model(val="").val is None

    def test_whitespace_only_becomes_none(self):
        assert _Model(val="   ").val is None

    def test_real_value_passes_through(self):
        assert _Model(val="hello").val == "hello"

    def test_none_passes_through(self):
        assert _Model(val=None).val is None

    def test_omitted_uses_default(self):
        assert _Model().val is None
