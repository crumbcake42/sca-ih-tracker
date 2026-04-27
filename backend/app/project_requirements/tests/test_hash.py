"""
Unit tests for hash_template_params().

Verifies that the canonicalization is deterministic and key-order independent,
which is load-bearing for the uniqueness constraint on wa_code_requirement_triggers.
"""

from app.project_requirements.services import hash_template_params


class TestHashTemplateParams:
    def test_empty_dict_is_stable(self):
        assert hash_template_params({}) == hash_template_params({})

    def test_key_order_does_not_affect_hash(self):
        a = hash_template_params({"a": 1, "b": 2})
        b = hash_template_params({"b": 2, "a": 1})
        assert a == b

    def test_different_values_produce_different_hashes(self):
        assert hash_template_params({"a": 1}) != hash_template_params({"a": 2})

    def test_different_keys_produce_different_hashes(self):
        assert hash_template_params({"a": 1}) != hash_template_params({"b": 1})

    def test_nested_dict_key_order_independent(self):
        a = hash_template_params({"outer": {"x": 1, "y": 2}})
        b = hash_template_params({"outer": {"y": 2, "x": 1}})
        assert a == b

    def test_list_order_is_preserved(self):
        # List order is semantic — [1, 2] and [2, 1] must hash differently.
        assert hash_template_params({"items": [1, 2]}) != hash_template_params({"items": [2, 1]})

    def test_returns_64_char_hex_string(self):
        result = hash_template_params({"key": "value"})
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_repeated_calls_are_identical(self):
        params = {"document_type": "SURVEY_REPORT", "is_required": True}
        assert hash_template_params(params) == hash_template_params(params)
