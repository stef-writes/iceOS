"""JSON Schema validation utilities for node input/output schemas.

This module provides enhanced schema validation that supports both:
1. Simple type literals (backward compatible): {"name": "str", "count": "int"}
2. Full JSON Schema format: {"type": "object", "properties": {...}}

This enables richer validation for the canvas UI and better error messages.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple, Type, Optional, Union
from pydantic import BaseModel

from jsonschema import Draft7Validator


__all__ = [
    "validate_with_schema",
    "normalize_schema",
    "is_json_schema",
    "convert_simple_to_json_schema",
]


def is_json_schema(schema: Any) -> bool:
    """Check if the given schema is a valid JSON Schema (not a simple type literal).
    
    Args:
        schema: The schema to check
        
    Returns:
        True if it's a JSON Schema (has 'type' or '$ref' at root level)
    """
    if not isinstance(schema, dict):
        return False
    
    # JSON Schema typically has 'type', '$ref', 'properties', 'items', etc at root
    json_schema_keywords = {
        'type', '$ref', '$schema', 'properties', 'items', 
        'required', 'additionalProperties', 'allOf', 'anyOf', 'oneOf'
    }
    
    return bool(json_schema_keywords.intersection(schema.keys()))


def convert_simple_to_json_schema(simple_schema: Dict[str, str]) -> Dict[str, Any]:
    """Convert simple type literal schema to JSON Schema format.
    
    Args:
        simple_schema: Dict with string type literals like {"name": "str", "count": "int"}
        
    Returns:
        Full JSON Schema dict
        
    Example:
        >>> convert_simple_to_json_schema({"name": "str", "age": "int"})
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name", "age"]
        }
    """
    type_mapping = {
        "str": "string",
        "int": "integer", 
        "float": "number",
        "bool": "boolean",
        "dict": "object",
        "list": "array",
        "list[str]": {"type": "array", "items": {"type": "string"}},
        "list[int]": {"type": "array", "items": {"type": "integer"}},
        "list[float]": {"type": "array", "items": {"type": "number"}},
        "list[bool]": {"type": "array", "items": {"type": "boolean"}},
        "list[dict]": {"type": "array", "items": {"type": "object"}},
    }
    
    properties = {}
    required = []
    
    for key, type_literal in simple_schema.items():
        if type_literal in type_mapping:
            mapped = type_mapping[type_literal]
            if isinstance(mapped, dict):
                properties[key] = mapped
            else:
                properties[key] = {"type": mapped}
            required.append(key)
        else:
            # Default to string for unknown types
            properties[key] = {"type": "string"}
            required.append(key)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False
    }


def normalize_schema(schema: Union[Dict[str, Any], Type[BaseModel], None]) -> Optional[Dict[str, Any]]:
    """Normalize various schema formats to JSON Schema.
    
    Args:
        schema: Can be:
            - None (returns None)
            - Pydantic model class (converts to JSON Schema)
            - Simple type literal dict (converts to JSON Schema)
            - Full JSON Schema dict (returns as-is)
            
    Returns:
        Normalized JSON Schema dict or None
    """
    if schema is None:
        return None
        
    # Handle Pydantic models
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return schema.model_json_schema()
    
    # Handle dict schemas
    if isinstance(schema, dict):
        # Check if it's already a JSON Schema
        if is_json_schema(schema):
            return schema
        else:
            # Convert simple format to JSON Schema
            return convert_simple_to_json_schema(schema)
    
    # Unknown format
    return None


def validate_with_schema(
    data: Any, 
    schema: Union[Dict[str, Any], Type[BaseModel], None],
    coerce_types: bool = True
) -> Tuple[bool, List[str], Any]:
    """Validate data against a schema with optional type coercion.
    
    Args:
        data: The data to validate
        schema: The schema (simple format, JSON Schema, or Pydantic model)
        coerce_types: If True, attempt to coerce string JSON to dict
        
    Returns:
        Tuple of (is_valid, errors, coerced_data)
    """
    errors: List[str] = []
    
    # Handle None schema
    if schema is None:
        return True, [], data
    
    # Normalize schema to JSON Schema format
    json_schema = normalize_schema(schema)
    if json_schema is None:
        errors.append("Invalid schema format")
        return False, errors, data
    
    # Attempt to coerce string data to JSON if needed
    coerced_data = data
    if coerce_types and isinstance(data, str) and json_schema.get("type") == "object":
        try:
            coerced_data = json.loads(data)
        except json.JSONDecodeError as e:
            errors.append(f"Failed to parse JSON string: {str(e)}")
            return False, errors, data
    
    # Validate with JSON Schema
    try:
        validator = Draft7Validator(json_schema)
        validation_errors = list(validator.iter_errors(coerced_data))
        
        if validation_errors:
            for error in validation_errors:
                # Format error path
                path = ".".join(str(p) for p in error.path) if error.path else "root"
                errors.append(f"{path}: {error.message}")
            return False, errors, coerced_data
            
        return True, [], coerced_data
        
    except Exception as e:
        errors.append(f"Schema validation error: {str(e)}")
        return False, errors, coerced_data


# Backward compatibility helpers
def is_valid_schema_dict(schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a schema dict (backward compatible with simple format).
    
    This maintains compatibility with the existing simple schema validation
    while also supporting full JSON Schema.
    """
    # Try to normalize it - if successful, it's valid
    try:
        normalized = normalize_schema(schema)
        if normalized is not None:
            # Validate the schema itself is well-formed
            Draft7Validator.check_schema(normalized)
            return True, []
        else:
            return False, ["Unable to normalize schema"]
    except Exception as e:
        return False, [f"Invalid schema: {str(e)}"] 