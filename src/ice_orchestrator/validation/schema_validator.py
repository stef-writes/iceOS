"""Schema validation for ScriptChain node outputs.

Extracted from `ScriptChain._is_output_valid` to improve separation of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from ice_core.models.node_models import NodeConfig


class SchemaValidator:  # – internal utility
    """Validates node outputs against declared schemas."""

    @staticmethod
    def is_output_valid(node: "NodeConfig", output: Any) -> bool:
        """Validate *output* against ``node.output_schema``.  Returns *True* when
        validation succeeds or no schema declared.

        Supports both *dict*-based schemas and Pydantic ``BaseModel`` subclasses to
        stay in sync with the flexible input validation strategy.
        """

        schema = getattr(node, "output_schema", None)
        if not schema:
            return True

        # --------------------------------------------------------------
        # Attempt to coerce *str* outputs into JSON when a schema exists
        # --------------------------------------------------------------
        # Many LLM calls return raw strings even when the prompt asks for
        # JSON.  To provide a consistent developer experience, we try to
        # parse such strings as JSON **once** before any further type
        # validation.  When parsing fails, the output is considered
        # invalid for schema-validated nodes so downstream mappings do
        # not break at runtime.
        if isinstance(output, str):
            try:
                import json  # local import to avoid startup overhead

                output = json.loads(output)
            except json.JSONDecodeError:
                # Raw string could not be parsed – treat as validation
                # failure so callers can surface helpful error messages.
                return False

        # ------------------------------------------------------------------
        # 1. Pydantic model --------------------------------------------------
        # ------------------------------------------------------------------
        try:
            from pydantic import BaseModel, ValidationError

            if isinstance(schema, type) and issubclass(schema, BaseModel):
                try:
                    schema.model_validate(output)  # type: ignore[arg-type]
                    return True
                except ValidationError:
                    return False
        except Exception:
            # Pydantic may not be importable in constrained envs – fall back.
            pass

        # ------------------------------------------------------------------
        # 2. dict schema – leverage nested validation helper -----------------
        # ------------------------------------------------------------------
        if isinstance(schema, dict):
            # Accept both {key: "type"} and {key: <type>} formats ------------
            normalized_schema: dict[str, type] = {}
            for key, expected in schema.items():
                if isinstance(expected, str):
                    try:
                        normalized_schema[key] = eval(expected)
                    except Exception:
                        # Fallback to 'Any' when type string cannot be resolved
                        from typing import Any  # local import to avoid top-level

                        normalized_schema[key] = Any  # type: ignore[assignment]
                else:
                    normalized_schema[key] = expected  # type: ignore[assignment]

            from ice_core.utils.nested_validation import validate_nested_output

            errors = validate_nested_output(output, normalized_schema)
            return len(errors) == 0

        # Unknown schema format – consider valid to avoid false negatives
        return True
