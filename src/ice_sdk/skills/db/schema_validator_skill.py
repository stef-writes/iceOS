from __future__ import annotations

import json
from typing import Any, Dict

from jsonschema import Draft7Validator, ValidationError  # type: ignore

from ..base import SkillBase
from ...utils.errors import SkillExecutionError

__all__ = ["SchemaValidatorSkill"]


class SchemaValidatorSkill(SkillBase):
    """Validate JSON data against a JSONSchema."""

    name: str = "schema_validator"
    description: str = "Validate JSON data against JSONSchema."
    tags = ["db", "schema", "validation"]

    def get_required_config(self):
        return []

    async def _execute_impl(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        schema = input_data.get("schema")
        data = input_data.get("data")
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