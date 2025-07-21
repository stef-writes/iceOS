from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Type, TypeVar

from ice_sdk.models.node_models import NodeConfig

T = TypeVar("T")


class TypeCoercionError(ValueError):
    """Raised when automatic type coercion fails."""


class TypeEnforcer:
    @classmethod
    def coerce(cls, value: Any, target_type: Type[T]) -> T:
        try:
            return target_type(value)
        except (TypeError, ValueError):
            raise TypeCoercionError(f"Cannot coerce {value} to {target_type}")

    @classmethod
    def enforce_inputs(
        cls, node: NodeConfig, inputs: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Coerce *inputs* according to the *node* ``input_schema`` mapping."""

        coerced: MutableMapping[str, Any] = {}
        for key, value in inputs.items():
            target = node.input_schema.get(key, Any)  # type: ignore[index]
            coerced[key] = cls.coerce(value, target)  # type: ignore[arg-type]
        return dict(coerced)
