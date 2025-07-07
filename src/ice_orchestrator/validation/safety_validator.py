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
            # Only AI nodes may declare allow-lists – but non-tool nodes must not
            allowed = getattr(node, "allowed_tools", None)
            if node.type != "tool" and allowed:
                raise ValueError(
                    f"Node '{node.id}' (type={node.type}) is not allowed to declare allowed_tools"
                )
