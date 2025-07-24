"""Backward compatibility executors for tests.

This module provides the builtin executors that tests expect.
The actual implementations have been moved to unified.py.
"""

from ice_orchestrator.execution.executors.unified import (
    tool_executor,
    llm_executor,
    agent_executor,
    condition_executor,
    nested_chain_executor,
)

# Note: The following executors don't exist yet:
# - unit_executor
# - workflow_executor  
# - loop_executor
# - parallel_executor
# - code_executor
# They will be added when their corresponding node configs are created

__all__ = [
    "tool_executor",
    "llm_executor", 
    "agent_executor",
    "condition_executor",
    "nested_chain_executor",
] 