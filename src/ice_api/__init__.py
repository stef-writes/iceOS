"""
Gaffer - AI Workflow Orchestration System
"""

from fastapi import FastAPI

from ice_orchestrator import ScriptChain

app = FastAPI(title="IceOS API")

__version__ = "0.1.0"

__all__ = ["app", "ScriptChain"]
