"""Context management helpers (session state, stores, etc.) shared by agents and orchestrator."""

from __future__ import annotations

from ice_sdk.context.scoped_context_store import ScopedContextStore
from ice_sdk.context.session_state import SessionState

from .async_manager import GraphContextManager  # async-first implementation
from .async_manager import AsyncGraphContextManager
from .memory import BaseMemory, NullMemory  # re-export for convenience
from .graph_analyzer import GraphAnalyzer, GraphMetrics, DependencyImpact  # Graph intelligence

__all__: list[str] = [
    "GraphContextManager",
    "SessionState",
    "ScopedContextStore",
    "BaseMemory",
    "NullMemory",
    "AsyncGraphContextManager",
    "GraphAnalyzer",
    "GraphMetrics", 
    "DependencyImpact",
]
