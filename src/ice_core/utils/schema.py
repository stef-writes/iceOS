"""Utility helpers for validating *input_schema* / *output_schema* dicts.

This module now supports both:
1. Simple type literals (backward compatible):
   - Scalar types: "str", "int", "float", "bool"  
   - Lists: "list[str]", "list[int]"
   - Objects: "dict"

2. Full JSON Schema format:
   - {"type": "object", "properties": {...}}
   - Rich validation with required fields, patterns, etc.

For complex nested objects, you can use either:
- Pydantic model classes  
- Full JSON Schema definitions
- Simple type literals (limited validation)
"""

from __future__ import annotations

import inspect
import re
from typing import Any, Dict, List, Tuple, Type

from pydantic import BaseModel  # Imported locally in _validate_schema_value

_SCALAR_MAP: Dict[str, Type[Any]] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "dict": dict,  # generic mapping / object
}

_LIST_RE = re.compile(r"^list\s*\[\s*([a-zA-Z0-9_]+)\s*]$")

__all__ = [
    "parse_type_literal",
    "is_valid_schema_dict",
]


def parse_type_literal(literal: str) -> Type[Any] | None:
    """Return concrete Python *type* for *literal* or *None* when unsupported."""

    lit = literal.strip()
    # 1. scalar -----------------------------------------------------------
    if lit in _SCALAR_MAP:
        return _SCALAR_MAP[lit]

    # 2. list[field] ------------------------------------------------------
    m = _LIST_RE.match(lit)
    if m:
        inner = m.group(1)
        inner_t = _SCALAR_MAP.get(inner)
        if inner_t is not None:
            return list

    return None


def _validate_schema_value(value: Any) -> bool:
    """Validate a single schema value entry."""
    # Allow Pydantic models
    if inspect.isclass(value) and issubclass(value, BaseModel):
        return True

    # Allow Python types
    if isinstance(value, type) and value in {str, int, float, bool, dict, list}:
        return True

    # Validate string literals
    if isinstance(value, str):
        # Block union types and malformed containers
        if "|" in value or "Union" in value:
            return False
        if value.count("[") != value.count("]"):
            return False

        # Parse the literal
        parsed_type = parse_type_literal(value)
        return parsed_type is not None

    return False


def is_valid_schema_dict(schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate *schema* dict; returns (is_valid, list_of_errors).

    Now supports both simple type literals and full JSON Schema format.
    """
    # Import the new JSON Schema validator
    from ice_core.utils.json_schema import is_valid_schema_dict as json_schema_validate

    # Use the new validator that handles both formats
    return json_schema_validate(schema)
