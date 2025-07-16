import pytest
from pydantic import BaseModel

from ice_core.utils.coercion import coerce_types, coerce_value
from ice_sdk.core.validation import SchemaValidationError, validate_or_raise

# ---------------------------------------------------------------------------
# Tests for utils.type_coercion
# ---------------------------------------------------------------------------


def test_coerce_value_basic_types() -> None:
    """coerce_value should correctly convert across the supported primitives."""

    # Int conversions
    assert coerce_value("42", int) == 42
    assert coerce_value("3.0", int) == 3
    assert coerce_value(4.5, int) == 4

    # Float conversions
    assert pytest.approx(coerce_value("3.14", float), 0.001) == 3.14  # type: ignore[arg-type]

    # Bool conversions
    assert coerce_value("Yes", bool) is True
    assert coerce_value(0, bool) is False

    # Str conversion is always a pass-through to str()
    assert coerce_value(123, str) == "123"


def test_coerce_value_invalid_int() -> None:
    """Invalid numeric strings raise ValueError."""

    with pytest.raises(ValueError):
        coerce_value("nan", int)


class _PersonModel(BaseModel):
    name: str
    age: int


@pytest.mark.parametrize(
    "output,schema,expected",
    [
        (
            {"age": "25", "name": "Alice"},
            {"age": "int", "name": "str"},
            {"age": 25, "name": "Alice"},
        ),
        ({"name": "Bob", "age": "30"}, _PersonModel, {"name": "Bob", "age": 30}),
    ],
)
def test_coerce_types_success(output, schema, expected):  # type: ignore[annotation-unchecked]
    """coerce_types should return properly coerced dict for valid input."""

    assert coerce_types(output, schema) == expected


def test_coerce_types_error_collection() -> None:
    """coerce_types should aggregate and report errors when coercion fails."""

    with pytest.raises(ValueError):
        coerce_types({"age": "abc"}, {"age": "int"})


# ---------------------------------------------------------------------------
# Tests for core.validation.validate_or_raise
# ---------------------------------------------------------------------------


def test_validate_or_raise_with_none_schema() -> None:
    """Passing *None* as schema must skip validation silently."""

    validate_or_raise({"anything": 123}, None)  # Should not raise


class _PetModel(BaseModel):
    name: str
    kind: str


def test_validate_or_raise_with_pydantic_model() -> None:
    """Both model class and instance must validate correctly."""

    payload = {"name": "Fluffy", "kind": "cat"}

    # Model class
    validate_or_raise(payload, _PetModel)

    # Model instance
    validate_or_raise(payload, _PetModel(name="Fluffy", kind="cat"))

    # Invalid payload – missing required field
    with pytest.raises(SchemaValidationError):
        validate_or_raise({"name": "Fluffy"}, _PetModel)


_JSON_SCHEMA = {
    "required": ["title"],
    "properties": {
        "title": {"type": "string"},
        "views": {"type": "number"},
    },
}


def test_validate_or_raise_with_mapping_schema() -> None:
    """validate_or_raise should enforce a minimal JSON-Schema subset."""

    valid = {"title": "IceOS", "views": 1_234}
    validate_or_raise(valid, _JSON_SCHEMA)

    missing_required = {"views": 10}
    with pytest.raises(SchemaValidationError):
        validate_or_raise(missing_required, _JSON_SCHEMA)

    wrong_type = {"title": 123}
    with pytest.raises(SchemaValidationError):
        validate_or_raise(wrong_type, _JSON_SCHEMA)
