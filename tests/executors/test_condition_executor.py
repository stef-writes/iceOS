from typing import Any

import pytest

from ice_sdk.executors.condition import condition_executor  # noqa: E402
from ice_sdk.models.node_models import ConditionNodeConfig


class DummyChain:  # minimal stub satisfying ScriptChainLike
    context_manager: Any
    _agent_cache: dict = {}

    async def execute(self):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_condition_true() -> None:
    cfg = ConditionNodeConfig(id="cond1", name="cond1", type="condition", expression="True")
    result = await condition_executor(DummyChain(), cfg, {})  # type: ignore[arg-type]
    assert result.success is True
    assert result.output == {"result": True}


@pytest.mark.asyncio
async def test_condition_false() -> None:
    cfg = ConditionNodeConfig(id="cond2", name="cond2", type="condition", expression="False")
    result = await condition_executor(DummyChain(), cfg, {})  # type: ignore[arg-type]
    assert result.success is True  # evaluation succeeds even if result False
    assert result.output == {"result": False}


@pytest.mark.asyncio
async def test_condition_error() -> None:
    cfg = ConditionNodeConfig(id="cond3", name="cond3", type="condition", expression="1/0")
    result = await condition_executor(DummyChain(), cfg, {})  # type: ignore[arg-type]
    assert result.success is False
    assert result.error is not None 