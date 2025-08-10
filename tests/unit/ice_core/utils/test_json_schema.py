"""Unit tests for JSON Schema validation utilities."""

from pydantic import BaseModel

from ice_core.utils.json_schema import (
    convert_simple_to_json_schema,
    is_json_schema,
    is_valid_schema_dict,
    normalize_schema,
    validate_with_schema,
)


class TestIsJsonSchema:
    """Test JSON Schema detection."""

    def test_detects_json_schema_with_type(self):
        """It should detect schemas with 'type' field."""
        assert is_json_schema({"type": "object"})
        assert is_json_schema({"type": "string"})
        assert is_json_schema({"type": "array", "items": {"type": "string"}})

    def test_detects_json_schema_with_properties(self):
        """It should detect schemas with 'properties' field."""
        assert is_json_schema({"properties": {"name": {"type": "string"}}})

    def test_rejects_simple_schema(self):
        """It should reject simple type literal schemas."""
        assert not is_json_schema({"name": "str"})
        assert not is_json_schema({"count": "int"})

    def test_rejects_non_dict(self):
        """It should reject non-dict inputs."""
        assert not is_json_schema("string")
        assert not is_json_schema(123)
        assert not is_json_schema(None)


class TestConvertSimpleToJsonSchema:
    """Test conversion from simple format to JSON Schema."""

    def test_converts_basic_types(self):
        """It should convert basic type literals."""
        result = convert_simple_to_json_schema(
            {"name": "str", "age": "int", "weight": "float", "active": "bool"}
        )

        assert result == {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "weight": {"type": "number"},
                "active": {"type": "boolean"},
            },
            "required": ["name", "age", "weight", "active"],
            "additionalProperties": False,
        }

    def test_converts_list_types(self):
        """It should convert list type literals."""
        result = convert_simple_to_json_schema(
            {"tags": "list[str]", "scores": "list[int]"}
        )

        assert result["properties"]["tags"] == {
            "type": "array",
            "items": {"type": "string"},
        }
        assert result["properties"]["scores"] == {
            "type": "array",
            "items": {"type": "integer"},
        }

    def test_converts_dict_type(self):
        """It should convert dict type literal."""
        result = convert_simple_to_json_schema({"data": "dict"})
        assert result["properties"]["data"] == {"type": "object"}


class TestNormalizeSchema:
    """Test schema normalization."""

    def test_normalizes_none(self):
        """It should return None for None input."""
        assert normalize_schema(None) is None

    def test_normalizes_pydantic_model(self):
        """It should convert Pydantic models to JSON Schema."""

        class TestModel(BaseModel):
            name: str
            age: int

        result = normalize_schema(TestModel)
        assert result is not None
        assert "properties" in result
        assert "name" in result["properties"]
        assert "age" in result["properties"]

    def test_normalizes_json_schema(self):
        """It should return JSON Schema as-is."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        assert normalize_schema(schema) == schema

    def test_normalizes_simple_schema(self):
        """It should convert simple schema to JSON Schema."""
        simple = {"name": "str", "age": "int"}
        result = normalize_schema(simple)
        assert result["type"] == "object"
        assert "properties" in result


class TestValidateWithSchema:
    """Test data validation against schemas."""

    def test_validates_simple_schema(self):
        """It should validate data against simple schema."""
        schema = {"name": "str", "age": "int"}

        # Valid data
        is_valid, errors, _ = validate_with_schema({"name": "John", "age": 30}, schema)
        assert is_valid
        assert errors == []

        # Invalid data - missing field
        is_valid, errors, _ = validate_with_schema({"name": "John"}, schema)
        assert not is_valid
        assert any("age" in error for error in errors)

    def test_validates_json_schema(self):
        """It should validate data against JSON Schema."""
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "age": {"type": "integer", "minimum": 0, "maximum": 150},
            },
            "required": ["email"],
        }

        # Valid data
        is_valid, errors, _ = validate_with_schema(
            {"email": "user@example.com", "age": 25}, schema
        )
        assert is_valid

        # Invalid age
        is_valid, errors, _ = validate_with_schema(
            {"email": "user@example.com", "age": 200}, schema
        )
        assert not is_valid
        assert any("maximum" in error for error in errors)

    def test_coerces_json_string(self):
        """It should coerce JSON strings when appropriate."""
        schema = {"name": "str", "age": "int"}

        # JSON string input
        is_valid, errors, coerced = validate_with_schema(
            '{"name": "John", "age": 30}', schema, coerce_types=True
        )
        assert is_valid
        assert coerced == {"name": "John", "age": 30}

    def test_validates_pydantic_model(self):
        """It should validate against Pydantic model schemas."""

        class UserModel(BaseModel):
            name: str
            age: int

        is_valid, errors, _ = validate_with_schema(
            {"name": "John", "age": 30}, UserModel
        )
        assert is_valid


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_is_valid_schema_dict_simple(self):
        """It should validate simple schemas."""
        # Valid simple schema
        is_valid, errors = is_valid_schema_dict({"name": "str", "count": "int"})
        assert is_valid
        assert errors == []

    def test_is_valid_schema_dict_json_schema(self):
        """It should validate JSON Schemas."""
        # Valid JSON Schema
        is_valid, errors = is_valid_schema_dict(
            {"type": "object", "properties": {"name": {"type": "string"}}}
        )
        assert is_valid
        assert errors == []

    def test_is_valid_schema_dict_invalid(self):
        """It should reject invalid schemas."""
        # Invalid JSON Schema
        is_valid, errors = is_valid_schema_dict({"type": "invalid_type"})
        assert not is_valid
        assert len(errors) > 0
