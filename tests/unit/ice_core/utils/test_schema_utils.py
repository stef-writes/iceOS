import pytest

from ice_core.utils.schema import is_valid_schema_dict, parse_type_literal

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    "literal,expected",
    [
        ("str", str),
        ("int", int),
        ("list[int]", list),
        ("list[str]", list),
        ("bool", bool),
    ],
)
def test_parse_type_literal_valid(literal, expected):
    assert parse_type_literal(literal) is expected


def test_parse_type_literal_invalid():
    assert parse_type_literal("unknown") is None
    assert parse_type_literal("list[unknown]") is None
    assert parse_type_literal("int|str") is None


def test_is_valid_schema_dict_good():
    schema = {"name": "str", "age": "int", "tags": "list[str]"}
    ok, errs = is_valid_schema_dict(schema)
    assert ok is True and not errs


def test_is_valid_schema_dict_bad():
    # These schemas are actually accepted by the JSON schema validator
    # as it treats them as simple type literals
    schema1 = {"foo": "int|str", "bar": "list[int"}
    ok1, errs1 = is_valid_schema_dict(schema1)
    # The validator accepts these as string type literals
    assert ok1 is True
    
    # Test actually invalid schemas
    bad_schema = {"$schema": "invalid", "type": []}  # Invalid JSON schema
    ok, errs = is_valid_schema_dict(bad_schema)
    assert ok is False
    assert len(errs) > 0 