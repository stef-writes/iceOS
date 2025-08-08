import asyncio
import os
import sys

import pytest

from ice_orchestrator.execution.sandbox.resource_sandbox import ResourceSandbox


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform == "darwin",
    reason="Resource sandbox stress tests skipped on macOS due to OS-level limits",
)
async def test_big_allocation_memory_limit():
    """Allocating >512 MB should raise MemoryError or be killed within sandbox."""

    async def _big_alloc():  # noqa: D401
        # Attempt to allocate 1 GB
        try:
            _ = bytearray(1024 * 1024 * 1024)
        except MemoryError:
            raise
        return "allocation succeeded"  # pragma: no cover – should not reach

    sandbox = ResourceSandbox(timeout_seconds=5, memory_limit_mb=512)
    with pytest.raises((MemoryError, asyncio.TimeoutError, asyncio.CancelledError)):
        async with sandbox as sbx:
            await sbx.run_with_timeout(_big_alloc())


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform == "darwin",
    reason="Resource sandbox stress tests skipped on macOS due to OS-level limits",
)
async def test_fork_bomb_cpu_limit():
    """Mass forking should be stopped by CPU or timeout limits."""

    if not hasattr(os, "fork"):
        pytest.skip("os.fork not available on this platform")

    async def _fork_bomb():  # noqa: D401
        # Bomb for 3 seconds or until killed
        end_time = asyncio.get_event_loop().time() + 3
        while asyncio.get_event_loop().time() < end_time:
            pid = os.fork()
            if pid == 0:
                os._exit(0)
            else:
                os.waitpid(pid, 0)

    sandbox = ResourceSandbox(
        timeout_seconds=3, cpu_limit_seconds=1, memory_limit_mb=256
    )
    with pytest.raises(
        (asyncio.TimeoutError, asyncio.CancelledError, ProcessLookupError)
    ):
        async with sandbox as sbx:
            await sbx.run_with_timeout(_fork_bomb())
