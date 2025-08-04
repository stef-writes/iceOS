"""Stable, minimal public API for programmatic and AI-powered blueprint generation.

Only symbols re-exported here are guaranteed to remain stable across minor
versions. Both human developers and AI tools should import from this module
instead of reaching into internal sub-packages.
"""

from __future__ import annotations

from ice_builder.dsl.decorators import tool as tool  # noqa: F401

# Re-export Workflow DSL (Programmatic) ---------------------------------------
from ice_builder.dsl.workflow import WorkflowBuilder as WorkflowBuilder  # noqa: F401

# Re-export NL generation (AI-powered) ----------------------------------------
from ice_builder.nl import append_tool_node as append_tool_node  # noqa: F401
from ice_builder.nl import (  # noqa: F401
    create_partial_blueprint as create_partial_blueprint,
)
from ice_builder.nl import (  # Legacy NL helpers; noqa: F401
    generate_blueprint as generate_blueprint,
)
from ice_builder.nl import (  # noqa: F401
    generate_blueprint_interactive as generate_blueprint_interactive,
)

# Frequently-used node model classes (optional convenience) -------------------
from ice_core.models import LLMOperatorConfig as LLMOperatorConfig  # noqa: F401
from ice_core.models import ToolNodeConfig as ToolNodeConfig  # noqa: F401

# MCP / Blueprint models for JSON-only generation ----------------------------
from ice_core.models.mcp import Blueprint as Blueprint  # noqa: F401
from ice_core.models.mcp import NodeSpec as NodeSpec  # noqa: F401
from ice_core.models.mcp import PartialBlueprint as PartialBlueprint  # noqa: F401
from ice_core.models.mcp import PartialNodeSpec as PartialNodeSpec  # noqa: F401

__all__: list[str] = [
    # DSL (Programmatic)
    "WorkflowBuilder",
    "tool",
    # NL (AI-powered)
    "generate_blueprint",
    "generate_blueprint_interactive",
    "create_partial_blueprint",
    "append_tool_node",
    # Optional helpers
    "ToolNodeConfig",
    "LLMOperatorConfig",
    "NodeSpec",
    "PartialNodeSpec",
    "Blueprint",
    "PartialBlueprint",
]
