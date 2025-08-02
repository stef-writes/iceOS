"""Stable, minimal public API for code-generators (e.g. *Frosty*).

Only symbols re-exported here are guaranteed to remain stable across minor
versions.  Code-gen tools **must import from this module** instead of reaching
into internal sub-packages.
"""

from __future__ import annotations

# Re-export Workflow DSL ------------------------------------------------------
from ice_builder.dsl.workflow import WorkflowBuilder as WorkflowBuilder  # noqa: F401
from ice_builder.dsl.decorators import tool as tool  # noqa: F401

# Frequently-used node model classes (optional convenience) -------------------
from ice_core.models import (
    ToolNodeConfig as ToolNodeConfig,  # noqa: F401
    LLMOperatorConfig as LLMOperatorConfig,  # noqa: F401
)

# MCP / Blueprint models for JSON-only generation ----------------------------
from ice_core.models.mcp import (
    NodeSpec as NodeSpec,  # noqa: F401
    PartialNodeSpec as PartialNodeSpec,  # noqa: F401
    Blueprint as Blueprint,  # noqa: F401
    PartialBlueprint as PartialBlueprint,  # noqa: F401
)

__all__: list[str] = [
    "WorkflowBuilder",
    "tool",
    # Optional helpers
    "ToolNodeConfig",
    "LLMOperatorConfig",
    "NodeSpec",
    "PartialNodeSpec",
    "Blueprint",
    "PartialBlueprint",
]
