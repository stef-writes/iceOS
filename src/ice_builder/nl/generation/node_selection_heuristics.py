"""Heuristics for selecting appropriate node types based on task characteristics.

This module provides deterministic rules for mapping task descriptions to the
appropriate iceOS node type (LLM, Agent, Tool, Swarm, etc.).
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Type

from ice_core.models.node_models import (
    AgentNodeConfig,
    BaseNodeConfig,
    CodeNodeConfig,
    ConditionNodeConfig,
    HumanNodeConfig,
    LLMOperatorConfig,
    LoopNodeConfig,
    MonitorNodeConfig,
    ParallelNodeConfig,
    RecursiveNodeConfig,
    SwarmNodeConfig,
    ToolNodeConfig,
    WorkflowNodeConfig,
)

# Mapping of pattern keywords to node type constructors
NODE_TYPE_PATTERNS: Dict[str, Type[BaseNodeConfig]] = {
    "llm": LLMOperatorConfig,
    "agent": AgentNodeConfig,
    "tool": ToolNodeConfig,
    "parallel": ParallelNodeConfig,
    "swarm": SwarmNodeConfig,
    "human": HumanNodeConfig,
    "loop": LoopNodeConfig,
    "recursive": RecursiveNodeConfig,
    "code": CodeNodeConfig,
    "condition": ConditionNodeConfig,
    "workflow": WorkflowNodeConfig,
    "monitor": MonitorNodeConfig,
}

# Capability-based heuristics for automatic node selection
CAPABILITY_HEURISTICS: Dict[str, Callable[[str], Optional[Type[BaseNodeConfig]]]] = {
    "requires_tools": lambda desc: AgentNodeConfig if "tool" in desc.lower() else None,
    "requires_memory": lambda desc: AgentNodeConfig if "remember" in desc.lower() else None,
    "requires_iteration": lambda desc: LoopNodeConfig if any(word in desc.lower() for word in ["repeat", "iterate", "loop"]) else None,
    "requires_parallelism": lambda desc: ParallelNodeConfig if any(word in desc.lower() for word in ["parallel", "concurrent", "simultaneously"]) else None,
    "requires_consensus": lambda desc: SwarmNodeConfig if any(word in desc.lower() for word in ["vote", "consensus", "committee"]) else None,
    "requires_approval": lambda desc: HumanNodeConfig if any(word in desc.lower() for word in ["approve", "review", "human"]) else None,
    "generates_code": lambda desc: CodeNodeConfig if any(word in desc.lower() for word in ["code", "script", "program"]) else None,
    "monitors_metrics": lambda desc: MonitorNodeConfig if any(word in desc.lower() for word in ["monitor", "watch", "alert"]) else None,
}


def select_node_type(
    task_description: str,
    explicit_type: Optional[str] = None,
) -> Type[BaseNodeConfig]:
    """Select the appropriate node type for a given task.
    
    Args:
        task_description: Natural language description of the task.
        explicit_type: Optional explicit node type (e.g., "llm", "agent").
        
    Returns:
        The appropriate NodeConfig class for the task.
        
    Example:
        >>> node_cls = select_node_type("Generate text based on prompt")
        >>> assert node_cls == LLMOperatorConfig
    """
    # 1. Use explicit type if provided
    if explicit_type and explicit_type.lower() in NODE_TYPE_PATTERNS:
        return NODE_TYPE_PATTERNS[explicit_type.lower()]
    
    # 2. Apply capability heuristics
    for capability, heuristic in CAPABILITY_HEURISTICS.items():
        node_type = heuristic(task_description)
        if node_type:
            return node_type
    
    # 3. Default to LLM operator for general text tasks
    return LLMOperatorConfig


def describe_node_capabilities() -> Dict[str, str]:
    """Return human-readable descriptions of each node type's capabilities.
    
    This is used in prompts to help LLMs understand the available options.
    """
    return {
        "llm": "Stateless text generation with a single prompt/response",
        "agent": "Stateful execution with tool access and memory",
        "tool": "Execute a specific pre-built function (CSV reader, API call, etc.)",
        "parallel": "Run multiple tasks concurrently",
        "swarm": "Multi-agent collaboration with voting/consensus",
        "human": "Request human input or approval",
        "loop": "Repeat a task until a condition is met",
        "recursive": "Break down complex tasks into subtasks",
        "code": "Execute arbitrary Python code in a sandbox",
        "condition": "Branch execution based on a boolean condition",
        "workflow": "Encapsulate a sub-workflow as a single node",
        "monitor": "Watch metrics and trigger alerts/actions",
    }