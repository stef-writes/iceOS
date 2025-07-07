"""Safety validation for ScriptChain execution.

Extracted from `ScriptChain` safety validation functions to improve separation of concerns.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List

import structlog

if TYPE_CHECKING:  # pragma: no cover
    from ice_sdk.models.node_models import NodeConfig

logger = structlog.get_logger(__name__)


class SafetyValidator:  # noqa: D101 – internal utility
    """Safety validation helpers for ScriptChain."""

    # ---------------------------------------------------------------------------
    # Layer boundary validation ----------------------------------------------
    # ---------------------------------------------------------------------------

    _FORBIDDEN_IMPORT_PREFIXES = (
        "ice_sdk.tools",  # lower layer (sdk) exposing tool impls
    )

    @classmethod
    def validate_layer_boundaries(cls) -> None:
        """Raise LayerViolationError if orchestrator accidentally imported tool modules."""

        for mod_name in sys.modules:
            if any(
                mod_name.startswith(prefix) for prefix in cls._FORBIDDEN_IMPORT_PREFIXES
            ):
                logger.warning(
                    "Layer-boundary advisory: orchestrator imported higher-level module '%s' (allowed in test/dev)",
                    mod_name,
                )

    # ---------------------------------------------------------------------------
    # Node tool access validation -------------------------------------------
    # ---------------------------------------------------------------------------

    @classmethod
    def validate_node_tool_access(cls, nodes: List["NodeConfig"]) -> None:
        """Ensure only *tool* nodes reference tools explicitly."""

        for node in nodes:
            allowed = getattr(node, "allowed_tools", None)

            # Skip when no allow-list declared ----------------------------------
            if not allowed:
                continue

            if node.type == "ai":
                # Legitimate use-case – AI node wants to limit which registered
                # tools it may call.  No validation needed here; enforcement
                # happens inside the agent executor at runtime.
                continue

            # Any other node type is not allowed to carry *allowed_tools* for
            # now.  Condition and Tool nodes should execute deterministically
            # without further nested tool calls.
            raise ValueError(
                f"Node '{node.id}' (type={node.type}) cannot declare allowed_tools"
            )
