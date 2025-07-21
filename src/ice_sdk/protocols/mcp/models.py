"""MCP protocol models - re-exported from core for backward compatibility.

This module re-exports the MCP models from ice_core.models.mcp to maintain
backward compatibility while consolidating the models in the core layer.
"""

from ice_core.models.mcp import (
    Blueprint,
    BlueprintAck,
    NodeSpec,
    RunAck,
    RunOptions,
    RunRequest,
    RunResult,
    uuid4_hex,
)

__all__ = [
    "Blueprint",
    "BlueprintAck",
    "NodeSpec",
    "RunAck",
    "RunOptions",
    "RunRequest",
    "RunResult",
    "uuid4_hex",
]
