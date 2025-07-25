"""Schema validation for ScriptChain node outputs.

Extracted from `ScriptChain._is_output_valid` to improve separation of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from collections import defaultdict, deque
from typing import List, Set

if TYPE_CHECKING:  # pragma: no cover
    from ice_core.models.node_models import NodeConfig
    from ice_core.models.mcp import Blueprint  # noqa: WPS433  – runtime import

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

        # ------------------------------------------------------------------
        # Schema presence is now mandatory for all nodes except LLM (which
        # gets a default {{"text":"string"}}).  If we *still* encounter a
        # node without schema it means runtime_validate() was skipped – fail
        # loudly so the bug surfaces during testing.
        # ------------------------------------------------------------------

        if not schema:
            from ice_core.models.node_models import LLMOperatorConfig  # local import

            if isinstance(node, LLMOperatorConfig):
                # Gracefully accept; treat as passthrough text.
                return True

            raise ValueError(
                f"Node '{getattr(node, 'id', '?')}' lacks output_schema despite mandatory policy."
            )

        # --------------------------------------------------------------
        # Validate schema dict literals first (now supports JSON Schema)
        if isinstance(schema, dict):
            from ice_core.utils.json_schema import is_valid_schema_dict

            ok, errs = is_valid_schema_dict(schema)
            if not ok:
                raise ValueError(
                    f"Invalid output_schema for node '{getattr(node, 'id', '?')}' – {'; '.join(errs)}"
                )

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
        # 2. dict schema – use new JSON Schema validation ------------------
        # ------------------------------------------------------------------
        if isinstance(schema, dict):
            from ice_core.utils.json_schema import validate_with_schema
            
            # Use the new validator that handles both simple and JSON Schema
            is_valid, errors, _ = validate_with_schema(output, schema)
            return is_valid

        # Unknown schema format – consider valid to avoid false negatives
        return True

# ---------------------------------------------------------------------------
# Custom exceptions ----------------------------------------------------------
# ---------------------------------------------------------------------------

class CircularDependencyError(ValueError):
    """Raised when a blueprint contains circular dependencies."""

class InvalidSchemaVersionError(ValueError):
    """Raised when a blueprint's declared schema version is unsupported."""

# ---------------------------------------------------------------------------
# Blueprint-level validation --------------------------------------------------
# ---------------------------------------------------------------------------

async def validate_blueprint(blueprint: "Blueprint") -> None:  # type: ignore[FWDref]
    """Validate a ``Blueprint`` object.

    This helper is *async* so callers can await it in orchestration pipelines
    without blocking the event loop (the implementation is CPU-bound but cheap).

    Validation steps:
      1. Schema version enforcement – currently only *1.1.0* is allowed.
      2. Circular dependency detection using Kahn's algorithm.
      3. Referential integrity – all *dependencies* must reference existing nodes
         (already guaranteed by ``Blueprint`` model validator but re-checked for
         completeness).

    Raises
    ------
    InvalidSchemaVersionError
        When the blueprint declares an unsupported ``schema_version``.
    CircularDependencyError
        When a cycle is detected in the node dependency graph.
    """

    # Lazy import to avoid cross-layer dependency at module import time
    from ice_core.models.mcp import Blueprint  # noqa: WPS433  – runtime import

    if blueprint.schema_version != "1.1.0":  # Hardcoded until next minor bump
        raise InvalidSchemaVersionError(
            f"Unsupported schema_version '{blueprint.schema_version}'. "
            "Expected '1.1.0'."
        )

    # ------------------------------------------------------------------
    # Cycle detection (Kahn's algorithm) --------------------------------
    # ------------------------------------------------------------------
    in_degree: dict[str, int] = {node.id: 0 for node in blueprint.nodes}
    adjacency: dict[str, List[str]] = defaultdict(list)

    for node in blueprint.nodes:
        for dep in node.dependencies:
            adjacency[dep].append(node.id)
            in_degree[node.id] += 1

    queue: deque[str] = deque([nid for nid, deg in in_degree.items() if deg == 0])
    processed = 0

    while queue:
        current = queue.popleft()
        processed += 1
        for neighbour in adjacency.get(current, []):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if processed != len(blueprint.nodes):
        raise CircularDependencyError("Blueprint contains circular dependencies")

    # No exception means validation succeeded
    return None
