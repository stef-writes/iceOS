"""
Gaffer - AI Workflow Orchestration System
"""

import warnings

from fastapi import FastAPI

from ice_orchestrator import Workflow as ScriptChain

# Deprecation notice for external consumers --------------------------------
warnings.warn(
    "`ice_api.ScriptChain` has been renamed to `Workflow`; update your imports in v1.",
    DeprecationWarning,
    stacklevel=2,
)

app = FastAPI(title="IceOS API")

__version__ = "0.1.0"

__all__ = ["app", "ScriptChain"]
