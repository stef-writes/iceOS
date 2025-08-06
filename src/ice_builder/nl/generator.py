"""Blueprint generator utilities for Frosty.

This module converts analysed intent fragments into *PartialBlueprint* objects
that can be incrementally validated and later executed by the orchestrator.

NEW (2025-07):
    • Each *tool* node gets its ``input_schema`` field auto-populated from the
      underlying ``ToolBase.get_input_schema`` result so the Canvas / MCP layer
      can provide accurate parameter forms.
    • A boolean ``progress_capable`` flag is attached – this will be *True* for
      subclasses of a future ``LongRunningToolBase`` that stream intermediate
      updates; for now the flag is always *False*.
"""

from __future__ import annotations

from typing import List

from ice_core.models.enums import NodeType
from ice_core.models.mcp import PartialBlueprint, PartialNodeSpec
from ice_core.registry import registry

__all__: list[str] = [
    "create_partial_blueprint",
    "append_tool_node",
]


def create_partial_blueprint(name: str) -> PartialBlueprint:
    """Return a new *empty* ``PartialBlueprint`` with the provided *name*."""
    return PartialBlueprint(schema_version="1.1.0", metadata={"name": name})


def append_tool_node(
    blueprint: PartialBlueprint,
    *,
    node_id: str,
    tool_name: str,
    dependencies: List[str] | None = None,
) -> None:
    """Append a *tool* node, auto-injecting input-schema metadata.

    Parameters
    ----------
    blueprint : PartialBlueprint
        The blueprint to mutate.
    node_id : str
        Unique node identifier within the blueprint.
    tool_name : str
        Registry name of the tool implementation.
    dependencies : list[str] | None, default ``None``
        Upstream node IDs this node depends on.
    """
    dependencies = dependencies or []

    # ------------------------------------------------------------------
    # Look-up the tool instance so we can retrieve its input schema.
    # ------------------------------------------------------------------
    try:
        tool_instance = registry.get_tool(tool_name)
    except Exception:  # noqa: BLE001 – propagate as validation error downstream
        # Add a stub node so incremental validation surfaces the missing tool.
        blueprint.add_node(
            PartialNodeSpec(
                id=node_id,
                type=NodeType.TOOL.value,
                dependencies=dependencies,
            )
        )
        return

    # Determine whether the tool supports progress events – currently always
    # False because LongRunningToolBase is not yet implemented.
    progress_capable = hasattr(tool_instance, "yield_progress")  # naive check

    # Try to get input schema, fall back to empty dict if not available
    try:
        input_schema = tool_instance.input_schema  # type: ignore[attr-defined]
    except AttributeError:
        try:
            input_schema = tool_instance.__class__.get_input_schema()  # type: ignore[attr-defined]
        except AttributeError:
            input_schema = {"type": "object", "properties": {}}

    # Create node with extra fields (allowed by model_config={"extra": "allow"})
    node = PartialNodeSpec(  # type: ignore[call-arg]
        id=node_id,
        type=NodeType.TOOL.value,
        dependencies=dependencies,
        # Extra fields for metadata
        input_schema=input_schema,  # type: ignore[arg-type]
        progress_capable=progress_capable,  # type: ignore[arg-type]
    )

    blueprint.add_node(node)
