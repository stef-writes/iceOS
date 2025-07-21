from __future__ import annotations

from typing import Any, Dict, Type

from ice_sdk.models.node_models import NodeConfig


class TypeCoercionError(ValueError):
    """Raised when automatic type coercion fails."""


class TypeEnforcer:
    @classmethod
    def coerce(cls, value: Any, target_type: Type) -> Any:
        try:
            return target_type(value)
        except (TypeError, ValueError):
            raise TypeCoercionError(f"Cannot coerce {value} to {target_type}")

    @classmethod
    def enforce_inputs(cls, node: NodeConfig, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {k: cls.coerce(v, node.input_schema[k]) for k, v in inputs.items()}
