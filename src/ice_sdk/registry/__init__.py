"""Unified public import surface for runtime registries.

External code should import registry helpers exclusively from this module to
avoid hard-coding disparate file paths.  All legacy modules continue to work
via thin shim re-exports (see individual sub-modules).

Example
-------
>>> from ice_sdk.registry import SkillRegistry
>>> SkillRegistry.register(...)
"""

from __future__ import annotations

from ice_sdk.capabilities.registry import CapabilityRegistry

# Canonical registries -------------------------------------------------------
from .node import NODE_REGISTRY as NodeRegistry  # – executor map
from .tool import ToolRegistry as ToolRegistry
from .tool import global_tool_registry as global_tool_registry
from .operator import OperatorRegistry as OperatorRegistry
from .operator import global_operator_registry as global_operator_registry
from .agent import AgentRegistry as AgentRegistry
from .agent import global_agent_registry as global_agent_registry

# ---------------------------------------------------------------------------
# Public API surface ---------------------------------------------------------

__all__: list[str] = [
    "NodeRegistry",
    "ToolRegistry",
    "OperatorRegistry",
    "global_tool_registry",
    "global_operator_registry",
    "CapabilityRegistry",
    "AgentRegistry",
    "global_agent_registry",
]
