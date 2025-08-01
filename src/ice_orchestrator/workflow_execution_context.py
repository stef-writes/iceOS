from __future__ import annotations

# ruff: noqa: E402

"""WorkflowExecutionContext relocated from *ice_sdk.orchestrator*.

No behavioural changes; path-only refactor.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple


class _BulkSaveProtocol(Protocol):  # pragma: no cover – duck-typing helper
    async def bulk_save(self, data: List[Tuple[str, Dict[str, Any]]]) -> None: ...

class WorkflowExecutionContext:
    """Workflow-scoped execution preferences and safety flags."""

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
    ) -> None:
        self.mode = mode
        self.require_json_output = require_json_output
        self.strict_validation = strict_validation
        self.user_preferences = user_preferences or {}

        self._store = store
        self._flush_threshold = max(1, int(flush_threshold))
        self._write_buffer: List[Tuple[str, Dict[str, Any]]] = []
        self._last_flush_ns: float = time.perf_counter_ns()

        for k, v in kwargs.items():
            setattr(self, k, v)

    # -------------------------------- persistence helpers -------------------
    async def persist_state(self, key: str, state: Dict[str, Any]) -> None:
        if self._store is None:
            return
        self._write_buffer.append((key, state))
        if len(self._write_buffer) >= self._flush_threshold:
            await self._flush()

    async def _flush(self) -> None:
        if self._store is None or not self._write_buffer:
            self._write_buffer.clear()
            return
        try:
            await self._store.bulk_save(self._write_buffer)
        finally:
            self._write_buffer.clear()
            self._last_flush_ns = time.perf_counter_ns()
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
