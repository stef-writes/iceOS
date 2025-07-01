"""DEPRECATED shim – use ``ice_sdk.orchestrator.base_script_chain`` instead.
# ruff: noqa

This module exists solely to keep *legacy import paths* working:

    from ice_orchestrator.base_script_chain import BaseScriptChain

The canonical implementation was moved to ``ice_sdk.orchestrator`` to honour
layer boundaries (SDK ← Orchestrator ← App).
"""

from warnings import warn

# Import canonical symbols *before* emitting deprecation to satisfy import-order lint.
from ice_sdk.orchestrator.base_script_chain import (  # noqa: E402
    BaseScriptChain,
    FailurePolicy,
)

warn(
    "Importing from 'ice_orchestrator.base_script_chain' is deprecated; "
    "import from 'ice_sdk.orchestrator.base_script_chain' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "BaseScriptChain",
    "FailurePolicy",
]
