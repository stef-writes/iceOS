# – docstrings kept minimal for internal module
from __future__ import annotations

import asyncio
from typing import Any, Dict

from pydantic import Field

# Import *sync* base class under a private alias to avoid shadowing
from .manager import GraphContext
from .manager import GraphContextManager as _SyncGraphContextManager


class BranchContext(GraphContext):
    """Context object scoped to a *single* branch inside a session.

    A *branch* is a logical execution fork inside a ScriptChain – e.g. when a
    *Condition* node spawns two separate execution paths.  Each branch keeps
    its own copy of the contextual key-value data so parallel updates do not
    overwrite each other.
    """

    # Optional mutable store that can diverge from the parent session context
    branch_data: Dict[str, Any] = Field(default_factory=dict)

# ---------------------------------------------------------------------
# Async-first implementation ------------------------------------------
# ---------------------------------------------------------------------

class GraphContextManager(_SyncGraphContextManager):
    """Async-aware variant of :class:`GraphContextManager`.

    Key improvements over the base implementation:
    1. Uses an :class:`asyncio.Lock` to protect state mutations so concurrent
       tasks cannot corrupt in-memory data structures.
    2. Provides branch-scoped context isolation via :pyattr:`branch_stores`.
       Each *branch_id* has its own :class:`BranchContext` that starts as a
       shallow copy of the parent session context.

    NOTE: Public *sync* methods from the parent class remain available for
    backward compatibility.  New async helpers should be preferred in
    concurrent code.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._async_lock: asyncio.Lock = asyncio.Lock()
        # branch_id -> BranchContext
        self._branch_stores: Dict[str, BranchContext] = {}

    # ---------------------------------------------------------------------
    # Branch helpers
    # ---------------------------------------------------------------------

    # Internal ------------------------------------------------------------
    def _ensure_branch_context(self, branch_id: str) -> BranchContext:
        """Return existing branch context or create a new one *without* touching
        the external async lock.

        This helper **must** be invoked with ``self._async_lock`` already
        acquired.  It exists to avoid *re-entrant* attempts to acquire the
        same ``asyncio.Lock`` (which would deadlock) when higher-level
        helpers such as :py:meth:`update_branch_context` need to lazily create
        a context while holding the lock.
        """

        if branch_id not in self._branch_stores:
            parent_ctx = self.get_context() or GraphContext(session_id="default")
            self._branch_stores[branch_id] = BranchContext(
                **parent_ctx.model_dump(exclude={"start_time"}),
                branch_data={},
            )
        return self._branch_stores[branch_id]

    # Public --------------------------------------------------------------
    async def get_branch_context(self, branch_id: str) -> BranchContext:
        """Return – and lazily create – the branch-isolated context."""
        async with self._async_lock:
            return self._ensure_branch_context(branch_id)

    async def update_branch_context(self, branch_id: str, data: Dict[str, Any]) -> None:
        """Atomically merge *data* into the branch context."""
        async with self._async_lock:
            ctx = self._ensure_branch_context(branch_id)
            ctx.branch_data.update(data)

    async def clear_branch_context(self, branch_id: str) -> None:
        """Remove branch context entirely (garbage-collect finished branches)."""
        async with self._async_lock:
            self._branch_stores.pop(branch_id, None)

    # ------------------------------------------------------------------
    # Overridden helpers that must be async-aware
    # ------------------------------------------------------------------
    async def async_execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Async-friendly wrapper around :py:meth:`GraphContextManager.execute_tool`."""
        async with self._async_lock:
            # Delegate to the existing implementation (which might be async
            # already depending on the tool).
            return await super().execute_tool(tool_name, **kwargs)

    # Convenience alias so callers don't need to remember *async_* prefix
    execute_tool_async = async_execute_tool


