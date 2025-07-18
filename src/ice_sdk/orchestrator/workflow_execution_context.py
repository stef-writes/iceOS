"""Shared runtime preferences and safety flags for workflow execution.

`WorkflowExecutionContext` travels alongside a running workflow, collecting
user preferences and enforcing validation or persistence policies.  It is
engine-agnostic and therefore usable with both the legacy `ScriptChain` (now
aliased as `Workflow`) and future orchestration engines.
"""
# ---------------------------------------------------------------------------
# Lightweight state persistence & batching ----------------------------------
# ---------------------------------------------------------------------------
import asyncio
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple

# A minimal callable protocol for a *bulk_save* method so we avoid mandatory
# concrete store dependencies.  Any custom implementation merely needs a
# coroutine ``bulk_save`` accepting ``List[Tuple[str, Dict[str, Any]]]``.


class _BulkSaveProtocol(Protocol):  # pragma: no cover – runtime duck-typing helper
    async def bulk_save(
        self, data: List[Tuple[str, Dict[str, Any]]]
    ) -> None:  # noqa: D401
        """Persist *data* atomically.  Implement in concrete store."""


class WorkflowExecutionContext:
    """
    Workflow-scoped execution preferences and safety flags.

    This object travels alongside a workflow run and centralises knobs such as
    *require_json_output* or *strict_validation*.  It is **engine-agnostic** and
    therefore applies equally to the legacy *ScriptChain* and the new
    *WorkflowEngine* implementations.
    """

    def __init__(
        self,
        mode: str = "auto",
        require_json_output: bool = False,
        strict_validation: bool = False,
        user_preferences: Optional[Dict[str, Any]] = None,
        *,
        store: Optional[_BulkSaveProtocol] = None,
        flush_threshold: int = 10,
        **kwargs: Any,
    ):
        self.mode = mode  # e.g., 'tool-calling', 'chat', 'summarization', etc.
        self.require_json_output = require_json_output
        self.strict_validation = strict_validation
        self.user_preferences = user_preferences or {}

        # ------------------------------------------------------------------
        # Internal write-buffer for batched persistence --------------------
        # ------------------------------------------------------------------
        self._store: Optional[_BulkSaveProtocol] = store
        self._flush_threshold: int = max(1, int(flush_threshold))
        self._write_buffer: List[Tuple[str, Dict[str, Any]]] = []
        self._last_flush_ns: float = time.perf_counter_ns()

        # Store any additional context fields so previous API remains intact
        for k, v in kwargs.items():
            setattr(self, k, v)

    # ------------------------------------------------------------------
    # Persistence helpers ----------------------------------------------
    # ------------------------------------------------------------------

    async def persist_state(self, key: str, state: Dict[str, Any]) -> None:
        """Queue *state* for persistence.  Flushes automatically when the
        write-buffer reaches *flush_threshold* items.  If no *store* is
        configured, the call becomes a no-op so existing usage is safe."""

        if self._store is None:
            return  # graceful degradation – nothing to persist

        self._write_buffer.append((key, state))

        if len(self._write_buffer) >= self._flush_threshold:
            await self._flush()

    async def _flush(self) -> None:
        """Persist all queued states using ``bulk_save`` then clear buffer."""

        if self._store is None or not self._write_buffer:
            self._write_buffer.clear()
            return

        try:
            await self._store.bulk_save(self._write_buffer)
        finally:
            self._write_buffer.clear()
            self._last_flush_ns = time.perf_counter_ns()
            # Give event-loop a chance – avoid starving in tight loops
            await asyncio.sleep(0)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "require_json_output": self.require_json_output,
            "strict_validation": self.strict_validation,
            "user_preferences": self.user_preferences,
            **{
                k: v
                for k, v in self.__dict__.items()
                if k
                not in {
                    "mode",
                    "require_json_output",
                    "strict_validation",
                    "user_preferences",
                }
            },
        }
