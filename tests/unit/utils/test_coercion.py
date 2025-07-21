from ice_sdk.utils.coercion import auto_coerce, schema_match


def test_auto_coerce():
    """Test the auto_coerce function with various input types."""
    # Test JSON string to dict conversion
    assert auto_coerce('{"a": 1}', {"type": "object"}) == {"a": 1}

    # Test JSON string to list conversion
    assert auto_coerce("[1, 2, 3]", {"type": "array"}) == [1, 2, 3]

    # Test single element to list conversion
    assert auto_coerce("text", {"type": "array"}) == ["text"]

    # Test type casting
    assert auto_coerce("5", {"type": "integer"}) == 5
    assert auto_coerce("3.14", {"type": "number"}) == 3.14
    assert auto_coerce("true", {"type": "boolean"}) is True
    assert auto_coerce(123, {"type": "string"}) == "123"

    # Test fallback behavior
    assert auto_coerce("invalid_json", {"type": "object"}) == "invalid_json"


def test_schema_match():
    """Test the schema_match function."""
    # Test matching schemas
    assert schema_match({"type": "string"}, {"type": "string"}) is True
    assert schema_match({"type": "integer"}, {"type": "integer"}) is True

    # Test non-matching schemas
    assert schema_match({"type": "string"}, {"type": "integer"}) is False
    assert schema_match({"type": "object"}, {"type": "array"}) is False

    # Test schemas without type
    assert schema_match({}, {}) is True
    assert schema_match({"type": "string"}, {}) is False
