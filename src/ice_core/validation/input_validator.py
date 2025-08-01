"""Input validation helpers for ToolBase and other nodes.

This module re-uses the generic JSON-Schema validator in
`ice_core.utils.json_schema` but provides a thin convenience wrapper that
returns the tuple `(ok, errors, coerced)` expected by ToolBase.

It exists in a separate module so we can import it lazily from ToolBase
without causing circular-import issues.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ice_core.utils.json_schema import validate_with_schema

__all__: list[str] = ["validate_tool_inputs"]

def validate_tool_inputs(schema: Dict[str, Any], inputs: Dict[str, Any]) -> Tuple[bool, List[str], Any]:
    """Validate *inputs* against *schema*.

    Parameters
    ----------
    schema : Dict[str, Any]
        JSON Schema dictionary describing the expected structure.
    inputs : Dict[str, Any]
        The runtime kwargs provided to the tool.

    Returns
    -------
    Tuple[bool, List[str], Any]
        *ok* flag, list of validation error strings, and (potentially)
        coerced input payload returned by the underlying validator.
    """

    # Delegate to the existing utility; no type coercion – kwargs come as dict.
    ok, errors, coerced = validate_with_schema(inputs, schema, coerce_types=False)
    return ok, errors, coerced
