from __future__ import annotations

from typing import Any, Dict

import pytest

from ice_core.models.node_models import (
    NestedChainConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from ice_orchestrator.execution.executors.builtin import nested_chain_executor

pytestmark = [pytest.mark.unit]


class _ChildChain:  # pylint: disable=too-few-public-methods
    """Minimal stub implementing async *execute* returning a fixed result."""

    async def execute(self):  # noqa: D401
        from datetime import datetime

        return NodeExecutionResult(
            success=True,
            output={"stats": {"value": 42}, "msg": "hello"},
            metadata=NodeMetadata(
                node_id="child",
                node_type="llm",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
            ),
        )


@pytest.mark.asyncio
async def test_nested_chain_executor_basic():
    cfg = NestedChainConfig(id="parent", type="nested_chain", chain=_ChildChain())

    res = await nested_chain_executor(None, cfg, {})  # type: ignore[arg-type]

    assert res.success is True
    assert res.output == {"stats": {"value": 42}, "msg": "hello"}


@pytest.mark.asyncio
async def test_nested_chain_executor_exposed_outputs():
    cfg = NestedChainConfig(
        id="parent2",
        type="nested_chain",
        chain=_ChildChain(),
        exposed_outputs={"the_value": "stats.value", "greeting": "msg"},
    )

    res = await nested_chain_executor(None, cfg, {})  # type: ignore[arg-type]
    assert res.output == {"the_value": 42, "greeting": "hello"} 