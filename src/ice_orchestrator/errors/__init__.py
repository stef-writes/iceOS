"""Orchestrator errors package.

Provides error types specific to the orchestration layer.
"""

# Import directly from SDK to avoid layer violations
from ice_core.exceptions import (
    CoreError as ChainError,
    CycleDetectionError as CircularDependencyError,
    CoreError as ScriptChainError,
)

__all__ = ["ChainError", "CircularDependencyError", "ScriptChainError"]
