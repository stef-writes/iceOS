"""Context management helpers (session state, stores, etc.) shared by agents and orchestrator."""

from __future__ import annotations

from ice_sdk.context.scoped_context_store import ScopedContextStore
from ice_sdk.context.session_state import SessionState

from .async_manager import GraphContextManager  # async-first implementation
from .async_manager import AsyncGraphContextManager
from .memory import (  # re-export for convenience
    BaseMemory,
    NullMemory,
    SQLiteVectorMemory,
)

__all__: list[str] = [
    "GraphContextManager",
    "SessionState",
    "ScopedContextStore",
    "BaseMemory",
    "SQLiteVectorMemory",
    "NullMemory",
    "AsyncGraphContextManager",
]
