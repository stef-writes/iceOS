"""Orchestrator errors package.

Provides error types specific to the orchestration layer.
"""

# Import directly from SDK to avoid layer violations
from ice_core.exceptions import CoreError as ChainError
from ice_core.exceptions import CoreError as ScriptChainError
from ice_core.exceptions import CycleDetectionError as CircularDependencyError

__all__ = ["ChainError", "CircularDependencyError", "ScriptChainError"]
