import json
from typing import Any, Mapping


def auto_coerce(value: Any, target_schema: Mapping[str, Any]) -> Any:
    """Enhanced coercion based on schema patterns seen in your examples."""
    # JSON string → dict/list
    if isinstance(value, str) and target_schema.get("type") in ["object", "array"]:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    # Single element → list
    if target_schema.get("type") == "array" and not isinstance(value, list):
        return [value]

    # Type casting
    type_map = {"integer": int, "number": float, "boolean": bool, "string": str}
    if target_schema.get("type") in type_map:
        try:
            return type_map[target_schema["type"]](value)
        except (ValueError, TypeError):
            pass

    return value  # Fallback to original value

def schema_match(
    source_schema: Mapping[str, Any], target_schema: Mapping[str, Any]
) -> bool:
    """Simplified schema compatibility check from your test cases."""
    return source_schema.get("type") == target_schema.get("type")
