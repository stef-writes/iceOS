from __future__ import annotations

"""Background task manager for scheduled network executions.

Tracks asyncio.Tasks spawned for *execute_scheduled* runs so they can be
cancelled on demand (e.g., when MCP server restarts or explicit cancellation
request is received).
"""

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class NetworkTaskManager:
    """Manage long-running scheduled network tasks."""

    def __init__(self) -> None:  # noqa: D401 – simple init
        self._tasks: Dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(
        self, network_id: str, coro: Any
    ) -> None:  # noqa: ANN001 – generic coro
        """Start *coro* as background task under *network_id* key."""
        async with self._lock:
            await self._cancel_unlocked(network_id)
            task = asyncio.create_task(
                self._wrap_coro(network_id, coro), name=f"network_{network_id}"
            )
            self._tasks[network_id] = task
            logger.info("[task_manager] started network %s", network_id)

    async def cancel(self, network_id: str) -> bool:
        """Cancel running task; return True if a task was cancelled."""
        async with self._lock:
            return await self._cancel_unlocked(network_id)

    async def shutdown(self) -> None:
        """Cancel all running tasks (graceful shutdown)."""
        async with self._lock:
            ids = list(self._tasks.keys())
            for nid in ids:
                await self._cancel_unlocked(nid)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _cancel_unlocked(self, network_id: str) -> bool:
        task = self._tasks.pop(network_id, None)
        if task:
            task.cancel()
            try:
                await task
            except Exception:
                pass
            logger.info("[task_manager] cancelled network %s", network_id)
            return True
        return False

    async def _wrap_coro(self, network_id: str, coro: Any) -> None:  # noqa: ANN001
        try:
            await coro
        except asyncio.CancelledError:
            logger.info("[task_manager] task for %s cancelled", network_id)
            raise
        except Exception as exc:
            logger.error(
                "[task_manager] network %s crashed: %s", network_id, exc, exc_info=True
            )
