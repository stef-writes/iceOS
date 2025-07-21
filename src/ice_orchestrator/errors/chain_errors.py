"""Shim re-exporting ScriptChain errors from legacy path.

This guarantees that importing via ``ice_orchestrator.errors.chain_errors`` or
``ice_orchestrator.chain_errors`` returns *identical* class objects.
"""

# NOTE: Import from ice_sdk.exceptions to respect layer boundaries
from ice_sdk.exceptions import CoreError as ScriptChainError
from ice_sdk.exceptions import CycleDetectionError as CircularDependencyError

# Alias for backward compatibility
ChainError = ScriptChainError

__all__ = [
    "ScriptChainError",
    "CircularDependencyError",
    "ChainError",
]
