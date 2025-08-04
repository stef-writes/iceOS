"""Natural Language Blueprint Generation Pipeline.

This package contains the multi-LLM orchestration logic that transforms
natural language specifications into validated iceOS Blueprints.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Tuple, Optional

if TYPE_CHECKING:
    from ice_core.models.mcp import Blueprint

from .interactive_pipeline import InteractiveBlueprintPipeline
from .multi_llm_orchestrator import MultiLLMOrchestrator

__all__ = [
    "generate_blueprint",
    "generate_blueprint_interactive", 
    "InteractiveBlueprintPipeline",
    "MultiLLMOrchestrator",
]


async def _generate_async(specification: str) -> Blueprint:
    """Async wrapper for blueprint generation.
    
    Args:
        specification: Natural language description of desired workflow.
        
    Returns:
        Validated Blueprint ready for execution.
    """
    orchestrator = MultiLLMOrchestrator(specification)
    return await orchestrator.generate()


def generate_blueprint(specification: str) -> Blueprint:
    """Generate an iceOS Blueprint from natural language specification.
    
    This is the main entry point for the AI pipeline. It orchestrates
    multiple specialized LLMs to:
    1. Extract intent and constraints
    2. Create a high-level execution plan
    3. Decompose into concrete node configurations
    4. Generate a Mermaid flow diagram
    5. Write code implementations where needed
    
    Args:
        specification: Free-text description of the desired workflow.
        
    Returns:
        A fully validated Blueprint object ready for compilation and execution.
        
    Example:
        >>> from ice_builder.nl import generate_blueprint
        >>> bp = generate_blueprint("Process CSV files and create a summary report")
        >>> print(f"Generated {len(bp.nodes)} nodes")
    """
    return asyncio.run(_generate_async(specification))


async def _generate_interactive_async(specification: str) -> Tuple[str, Optional[Blueprint]]:
    """Interactive blueprint generation with preview."""
    pipeline = InteractiveBlueprintPipeline(specification)
    
    # Generate preview
    mermaid, warnings, questions = await pipeline.generate_preview()
    
    # Auto-approve if no warnings
    if not warnings:
        blueprint = await pipeline.approve_and_generate()
        return mermaid, blueprint
    
    # Otherwise return preview for user review
    return mermaid, None


def generate_blueprint_interactive(specification: str) -> Tuple[str, Optional[Blueprint]]:
    """Generate blueprint with interactive preview and approval.
    
    This version shows a Mermaid diagram preview before generating the full
    blueprint, allowing users to review and modify the plan.
    
    Args:
        specification: Free-text description of the desired workflow.
        
    Returns:
        Tuple of (mermaid_preview, blueprint).
        If there are warnings, blueprint will be None until approved.
        
    Example:
        >>> from ice_builder.nl import generate_blueprint_interactive
        >>> mermaid, bp = generate_blueprint_interactive("Complex multi-agent task")
        >>> print(mermaid)  # Shows preview diagram
        >>> if bp is None:  # Has warnings, needs approval
        ...     # Review and approve or revise
    """
    return asyncio.run(_generate_interactive_async(specification))