import pytest

from ice_core.utils.schema import parse_type_literal, is_valid_schema_dict

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
    bad_schema = {"foo": "int|str", "bar": "list[int"}
    ok, errs = is_valid_schema_dict(bad_schema)
    assert ok is False
    assert len(errs) == 2 