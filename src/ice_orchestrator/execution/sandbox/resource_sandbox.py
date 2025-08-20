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
import os
import platform
import resource
from types import TracebackType
from typing import Optional, Type

from ice_core.metrics import SANDBOX_CPU_SECONDS, SANDBOX_MAX_RSS_BYTES

# Optional seccomp import (Linux only)
try:
    import seccomp  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    seccomp = None  # type: ignore


from typing import Awaitable, TypeVar

T = TypeVar("T")


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MEMORY_LIMIT_MB = 512
DEFAULT_CPU_LIMIT_SECONDS = 10


class ResourceSandbox(contextlib.AbstractAsyncContextManager["ResourceSandbox"]):
    """Resource limiter for executor coroutines."""

    def __init__(
        self,
        *,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
        cpu_limit_seconds: int = DEFAULT_CPU_LIMIT_SECONDS,
    ) -> None:
        self._timeout = timeout_seconds
        self._mem_bytes = memory_limit_mb * 1024 * 1024
        self._cpu_seconds = cpu_limit_seconds
        self._timeout_handle: Optional[asyncio.TimerHandle] = None
        # Metrics snapshot
        self._cpu_start: float | None = None
        self._rss_start: int | None = None
        # Original rlimits snapshot for restoration
        self._orig_limits: dict[int, tuple[int, int]] = {}

    # --------------------------------------------------------------
    # Async context management
    # --------------------------------------------------------------

    async def __aenter__(self) -> "ResourceSandbox":
        loop = asyncio.get_running_loop()
        # Schedule timeout cancellation.
        self._timeout_handle = loop.call_later(self._timeout, self._cancel_current_task)

        # Snapshot resource usage at entry for delta calculation
        usage = resource.getrusage(resource.RUSAGE_SELF)
        self._cpu_start = usage.ru_utime + usage.ru_stime
        self._rss_start = usage.ru_maxrss

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

        # Record resource usage metrics if snapshot available
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            cpu_end = usage.ru_utime + usage.ru_stime
            rss_end = usage.ru_maxrss
            if self._cpu_start is not None:
                SANDBOX_CPU_SECONDS.observe(max(cpu_end - self._cpu_start, 0.0))
            if self._rss_start is not None:
                # ru_maxrss is kilobytes on Linux, bytes on macOS/BSD.
                rss_bytes = (
                    rss_end * 1024 if resource.getpagesize() == 4096 else rss_end
                )
                # ru_maxrss is already cumulative (peak), so take end value.
                SANDBOX_MAX_RSS_BYTES.observe(rss_bytes)
        except Exception:
            # Metrics must never break sandbox teardown.
            pass

        # Restore original rlimits to avoid leaking constraints to other threads
        try:
            for res, limits in self._orig_limits.items():
                try:
                    resource.setrlimit(res, limits)
                except Exception:
                    pass
        except Exception:
            pass

        # Propagate exceptions (do not suppress)
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
            self._orig_limits[resource.RLIMIT_AS] = resource.getrlimit(
                resource.RLIMIT_AS
            )
            resource.setrlimit(resource.RLIMIT_AS, (self._mem_bytes, self._mem_bytes))
        except (ValueError, OSError):
            # macOS typically raises; ignore.
            pass
        # RLIMIT_CPU
        try:
            self._orig_limits[resource.RLIMIT_CPU] = resource.getrlimit(
                resource.RLIMIT_CPU
            )
            resource.setrlimit(
                resource.RLIMIT_CPU, (self._cpu_seconds, self._cpu_seconds)
            )
        except (ValueError, OSError):
            pass
        # Disable core dumps
        try:
            self._orig_limits[resource.RLIMIT_CORE] = resource.getrlimit(
                resource.RLIMIT_CORE
            )
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        except (ValueError, OSError):
            pass

    def _apply_seccomp(self) -> None:  # pragma: linux-only
        # Allow disabling seccomp in test/CI environments where thread creation is required
        if (
            os.getenv("ICE_DISABLE_SECCOMP", "0") == "1"
            or os.getenv("ICE_SKIP_STRESS", "0") == "1"
        ):
            return
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
            # Allow thread/process creation for runtime components and clean shutdown
            "clone",
            "set_robust_list",
            "set_tid_address",
        ]
        for name in allowed:
            try:
                filt.add_rule(seccomp.ALLOW, name)
            except Exception:
                pass
        filt.load()
