import asyncio
from typing import Any

import pytest

from ice_sdk.context.async_manager import AsyncGraphContextManager


@pytest.mark.asyncio
async def test_branch_isolation_concurrent_updates() -> None:  # noqa: D401
    mgr = AsyncGraphContextManager()
    # Establish a parent session context so branch contexts can inherit.
    mgr.get_context("sess_1")

    async def writer(branch: str, key: str, value: Any) -> None:  # noqa: D401, ANN001
        for _ in range(10):
            await mgr.update_branch_context(branch, {key: value})

    await asyncio.gather(
        writer("branch_a", "x", 1),
        writer("branch_b", "x", 2),
    )

    ctx_a = await mgr.get_branch_context("branch_a")
    ctx_b = await mgr.get_branch_context("branch_b")

    assert ctx_a.branch_data["x"] == 1  # noqa: S101
    assert ctx_b.branch_data["x"] == 2  # noqa: S101
    # Ensure isolation
    assert ctx_a.branch_data != ctx_b.branch_data  # noqa: S101
