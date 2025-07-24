"""Backward compatibility executors for tests.

This module provides the builtin executors that tests expect.
The actual implementations have been moved to unified.py.
"""

from ice_orchestrator.execution.executors.unified import (
    tool_executor,
    llm_executor,
    unit_executor,
    agent_executor,
    workflow_executor,
    condition_executor,
    loop_executor,
    parallel_executor,
    code_executor,
)

# Alias for backward compatibility  
nested_chain_executor = workflow_executor

__all__ = [
    "tool_executor",
    "llm_executor", 
    "unit_executor",
    "agent_executor",
    "workflow_executor",
    "condition_executor",
    "loop_executor",
    "parallel_executor",
    "code_executor",
    "nested_chain_executor",
] 