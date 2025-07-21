"""Lightweight schema validation helper used across the SDK.

The goal is *not* to offer a fully-featured JSONSchema engine but to provide a
convenient wrapper that is good enough for quick, synchronous checks inside
`AgentNode.execute` or any other internal helper that needs to assert the shape
of a dict prior to handing it to an LLM.

External side-effects are forbidden in *core* per Cursor Rule 2 – keep this file
pure Python with no network / file IO.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Mapping, Type

if TYPE_CHECKING:  # pragma: no cover – import only for type checkers & linters
    from ice_core.models.node_models import NodeConfig

from pydantic import BaseModel, ValidationError

__all__ = [
    "validate_or_raise",
]


class SchemaValidationError(ValueError):
    """Raised when `validate_or_raise` detects an invalid payload."""


def _validate_with_pydantic_model(
    data: Any, model: Type[BaseModel]
) -> None:  # noqa: D401
    """Validate *data* against a Pydantic model class and re-raise uniformly."""
    try:
        model.model_validate(data)  # type: ignore[arg-type]
    except ValidationError as exc:  # pragma: no cover – pure helper
        raise SchemaValidationError(str(exc)) from exc


def validate_or_raise(data: Any, schema: Any | None = None) -> None:  # noqa: D401
    """Validate *data* against *schema* or raise :class:`SchemaValidationError`.

    Parameters
    ----------
    data
        Arbitrary Python payload to validate.
    schema
        One of the following:
        • ``None`` – validation is skipped.
        • ``dict`` – assumed to be an *object schema* following the JSONSchema
          conventions; only ``required`` and top-level field names / types are
          enforced for now (kept intentionally minimal).
        • :class:`pydantic.BaseModel` subclass – full Pydantic validation.
        • :class:`pydantic.BaseModel` instance – ``model_validate`` against its
          class.

    The helper is intentionally *best-effort* – if validation fails, it raises
    an explicit :class:`SchemaValidationError`; otherwise it returns ``None``.
    """

    if schema is None:
        return  # Nothing to validate

    # Case 1 – Pydantic model class / instance --------------------------------
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        _validate_with_pydantic_model(data, schema)
        return
    if isinstance(schema, BaseModel):
        _validate_with_pydantic_model(data, schema.__class__)
        return

    # Case 2 – Very small subset of JSONSchema ---------------------------------
    if isinstance(schema, Mapping):
        required_fields = set(schema.get("required", []))
        props: dict[str, Any] = schema.get("properties", {})

        missing = required_fields - set(data.keys())
        if missing:
            raise SchemaValidationError(f"Missing required fields: {sorted(missing)}")

        # Rough type check (only *str* names -> *type* references extracted from
        # the JSONSchema-like dict). We purposefully keep this loose.
        for key, field_schema in props.items():
            if key not in data:
                continue  # handled above or optional
            expected_type = (
                field_schema.get("type") if isinstance(field_schema, Mapping) else None
            )
            if expected_type == "object" and not isinstance(data[key], Mapping):
                raise SchemaValidationError(
                    f"Field '{key}' expected object, got {type(data[key]).__name__}"
                )
            if expected_type == "string" and not isinstance(data[key], str):
                raise SchemaValidationError(
                    f"Field '{key}' expected string, got {type(data[key]).__name__}"
                )
            if expected_type == "number" and not isinstance(data[key], (int, float)):
                raise SchemaValidationError(
                    f"Field '{key}' expected number, got {type(data[key]).__name__}"
                )
        return

    # Unsupported schema type ---------------------------------------------------
    raise TypeError(
        "Unsupported schema type for validate_or_raise: " f"{type(schema).__name__}"
    )


def validate_io(
    node: "NodeConfig", inputs: Dict[str, Any], outputs: Dict[str, Any]
) -> None:
    # Input validation
    for key, schema in node.input_schema.items():
        actual = inputs.get(key)
        if not isinstance(actual, schema):
            raise TypeError(f"Input {key} expected {schema}, got {type(actual)}")

    # Output validation
    for key, schema in node.output_schema.items():
        actual = outputs.get(key)
        if not isinstance(actual, schema):
            raise TypeError(f"Output {key} expected {schema}, got {type(actual)}")
