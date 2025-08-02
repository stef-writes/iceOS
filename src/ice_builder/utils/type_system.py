from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Type, TypeVar

from ice_core.models.node_models import NodeConfig

T = TypeVar("T")

class TypeCoercionError(ValueError):
    """Raised when automatic type coercion fails."""

class TypeEnforcer:
    @classmethod
    def coerce(cls, value: Any, target_type: Type[T]) -> T:  # type: ignore[type-var]
        """Coerce *value* to *target_type* if callable, otherwise return as is."""
        try:
            if callable(target_type):
                return target_type(value)  # type: ignore[call-arg]
            return value  # type: ignore[return-value]
        except (TypeError, ValueError):
            raise TypeCoercionError(f"Cannot coerce {value} to {target_type}")

    @classmethod
    def enforce_inputs(
        cls, node: NodeConfig, inputs: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Coerce *inputs* according to the *node* ``input_schema`` mapping."""

        coerced: MutableMapping[str, Any] = {}
        for key, value in inputs.items():
            schema: Dict[str, Any] = (
                node.input_schema if isinstance(node.input_schema, dict) else {}
            )
            target = schema.get(key, Any)
            coerced[key] = cls.coerce(value, target)  # type: ignore[arg-type]
        return dict(coerced)
