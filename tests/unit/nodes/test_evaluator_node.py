import os

import pytest

from ice_orchestrator.execution.executors.evaluator import evaluator_executor
from ice_sdk.models.node_models import EvaluatorNodeConfig


class _DummyChain:  # Minimal stub
    pass


@pytest.mark.asyncio
async def test_evaluator_node_passes(monkeypatch):
    os.environ["ICE_SDK_FAST_TEST"] = "1"
    cfg = EvaluatorNodeConfig(id="eval1", reference="hello world", threshold=0.5)
    ctx = {"candidate": "hello world"}
    result = await evaluator_executor(_DummyChain(), cfg, ctx)  # type: ignore[arg-type]
    assert result.success is True
    assert result.output["passed"] is True
    assert result.output["score"] == 1.0


@pytest.mark.asyncio
async def test_evaluator_node_fails(monkeypatch):
    os.environ["ICE_SDK_FAST_TEST"] = "1"
    cfg = EvaluatorNodeConfig(id="eval2", reference="hello world", threshold=0.8)
    ctx = {"candidate": "goodbye"}
    result = await evaluator_executor(_DummyChain(), cfg, ctx)  # type: ignore[arg-type]
    assert result.success is True
    assert result.output["passed"] is False
    assert result.output["score"] == 0.0
