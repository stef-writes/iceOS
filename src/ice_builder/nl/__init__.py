"""Natural language processing for iceOS workflow creation.

This module provides the AI-powered natural language interface for creating
iceOS blueprints. It complements the programmatic DSL in ice_builder.dsl.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Re-export the generator utilities
from .generator import append_tool_node, create_partial_blueprint

# Import the main generation functions
from .generation import (
    InteractiveBlueprintPipeline,
    MultiLLMOrchestrator,
    generate_blueprint,
    generate_blueprint_interactive,
)

__all__ = [
    # Legacy generator functions
    "create_partial_blueprint",
    "append_tool_node",
    # Main NL generation API
    "generate_blueprint",
    "generate_blueprint_interactive",
    # Advanced usage
    "InteractiveBlueprintPipeline",
    "MultiLLMOrchestrator",
] 
