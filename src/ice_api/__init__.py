"""
Gaffer - AI Workflow Orchestration System
"""

from typing import Any

from fastapi import FastAPI

# NOTE: The legacy alias `ScriptChain` has been removed to comply with layer
# boundaries (ice_api must not import from *ice_orchestrator*). External
# clients should depend on the new `/v1/builder` + execution endpoints.

# We keep a stub symbol so that **runtime** code referencing
# `ice_api.ScriptChain` fails fast with a helpful error message instead of an
# opaque `ImportError`.  This avoids cross-layer imports while providing a
# smoother migration path.


class _RemovedScriptChain:  # – shim for backwards compatibility
    """Stub that raises informative error on usage."""

    def __getattr__(self, name: str) -> Any:  # – proxy shim
        raise ImportError(
            "`ice_api.ScriptChain` has been removed. Import `Workflow` from the"
            " public orchestrator client or migrate to the new execution API."
        )


# Expose the stub so attribute access is still possible (albeit unsupported)
ScriptChain = _RemovedScriptChain()  # type: ignore

app = FastAPI(title="IceOS API")

__version__ = "0.1.0"

__all__ = ["app", "ScriptChain"]
