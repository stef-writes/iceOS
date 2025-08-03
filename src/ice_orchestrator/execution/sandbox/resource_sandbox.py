from __future__ import annotations

"""Cross-executor resource sandbox context manager.

Applies:
1. RLIMIT_AS (virtual memory cap) – always attempted; ignored on macOS.
2. RLIMIT_CPU   – wall-clock cpu seconds cap.
3. seccomp-bpf   – Linux only; falls back silently when `seccomp` python module missing.
4. asyncio timeout – guaranteed coroutine cancel after *timeout_seconds*.

This consolidates duplicated sandbox logic so every executor
(tool, recursive, wasm, etc.) shares identical resource limits.
"""

import asyncio
import contextlib
import platform
import resource
from types import TracebackType
from typing import Optional, Type

# Optional seccomp import (Linux only)
try:
    import seccomp  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    seccomp = None  # type: ignore


from typing import Any, TypeVar, Awaitable

T = TypeVar("T")

class ResourceSandbox(contextlib.AbstractAsyncContextManager["ResourceSandbox"]):
    """Resource limiter for executor coroutines."""

    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
        memory_limit_mb: int = 512,
        cpu_limit_seconds: int = 10,
    ) -> None:
        self._timeout = timeout_seconds
        self._mem_bytes = memory_limit_mb * 1024 * 1024
        self._cpu_seconds = cpu_limit_seconds
        self._timeout_handle: Optional[asyncio.TimerHandle] = None

    # --------------------------------------------------------------
    # Async context management
    # --------------------------------------------------------------

    async def __aenter__(self) -> "ResourceSandbox":
        loop = asyncio.get_running_loop()
        # Schedule timeout cancellation.
        self._timeout_handle = loop.call_later(self._timeout, self._cancel_current_task)

        # Apply RLIMITs in the current (executor) process only.
        self._apply_rlimits()
        self._apply_seccomp()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> bool:  # noqa: D401 – returns False to propagate exceptions
        if self._timeout_handle:
            self._timeout_handle.cancel()
        # No exception suppression here.
        return False

    # --------------------------------------------------------------
    # Public helper
    # --------------------------------------------------------------

    async def run_with_timeout(self, coro: Awaitable[T]) -> T:
        """Run *coro* ensuring overall timeout."""
        return await asyncio.wait_for(coro, timeout=self._timeout)

    # --------------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------------

    def _cancel_current_task(self) -> None:  # pragma: no cover
        task = asyncio.current_task()
        if task and not task.done():
            task.cancel()

    def _apply_rlimits(self) -> None:
        # RLIMIT_AS (virtual memory)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (self._mem_bytes, self._mem_bytes))
        except (ValueError, OSError):
            # macOS typically raises; ignore.
            pass
        # RLIMIT_CPU
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (self._cpu_seconds, self._cpu_seconds))
        except (ValueError, OSError):
            pass
        # Disable core dumps
        try:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        except (ValueError, OSError):
            pass

    def _apply_seccomp(self) -> None:  # pragma: linux-only
        if platform.system() != "Linux" or seccomp is None:
            return  # no-op on non-Linux or missing module
        # Allow basic syscalls only (whitelist)
        filt = seccomp.SyscallFilter(defaction=seccomp.KILL)
        allowed = [
            "read",
            "write",
            "exit",
            "exit_group",
            "clock_gettime",
            "getpid",
            "futex",
            "nanosleep",
        ]
        for name in allowed:
            try:
                filt.add_rule(seccomp.ALLOW, name)
            except Exception:
                pass
        filt.load()
