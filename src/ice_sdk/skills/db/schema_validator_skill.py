from __future__ import annotations

from typing import Any, Dict

from jsonschema import Draft7Validator  # type: ignore

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["SchemaValidatorSkill"]


class SchemaValidatorSkill(SkillBase):
    """Validate JSON data against a JSONSchema."""

    name: str = "schema_validator"
    description: str = "Validate JSON data against JSONSchema."
    tags = ["db", "schema", "validation"]

    def get_required_config(self):
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
            raise SkillExecutionError("'schema' must be object")
        if data is None:
            raise SkillExecutionError("'data' required")

        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            msgs = [e.message for e in errors]
            return {"valid": False, "errors": msgs}
        return {"valid": True}
