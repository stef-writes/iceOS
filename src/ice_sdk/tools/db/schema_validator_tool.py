from __future__ import annotations

from typing import Any, ClassVar, Dict

from jsonschema import Draft7Validator  # type: ignore

from ...utils.errors import ToolExecutionError
from ..base import ToolBase
from ..base import ToolBase

__all__ = ["SchemaValidatorTool"]

class SchemaValidatorTool(ToolBase):
    """Validate database schema against a set of rules."""

    name: str = "schema_validator"
    description: str = "Validate database schema against a set of rules"
    tags: ClassVar[list[str]] = ["db", "schema", "validation"]

    def get_required_config(self) -> list[str]:
        return []

    async def _execute_impl(
        self,
        *,
        schema: Dict[str, Any] | None = None,
        data: Any | None = None,
        input_data: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if input_data is not None:
            schema = schema or input_data.get("schema")  # type: ignore[assignment]
            data = data or input_data.get("data")  # type: ignore[assignment]
        if not isinstance(schema, dict):
            raise ToolExecutionError("'schema' must be object")
        if data is None:
            raise ToolExecutionError("'data' required")

        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            msgs = [e.message for e in errors]
            return {"valid": False, "errors": msgs}
        return {"valid": True}
