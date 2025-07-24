import types
from typing import Any, Dict

import pytest

from ice_core.models.node_models import (
    LLMOperatorConfig,
    ToolNodeConfig,
    ConditionNodeConfig,
    LLMConfig,
)
from ice_core.models.enums import ModelProvider
from ice_orchestrator.execution.executors.builtin import llm_executor, tool_executor
from ice_orchestrator.execution.executors.condition import condition_executor

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helper stubs ----------------------------------------------------------------
# ---------------------------------------------------------------------------


class _StubContextManager:  # pylint: disable=too-few-public-methods
    async def execute_tool(self, name: str, **kwargs: Any) -> Dict[str, Any]:  # noqa: D401
        # Echo back to validate placeholder substitution
        return {"name": name, "args": kwargs}


class _StubChain:  # pylint: disable=too-few-public-methods
    context_manager = _StubContextManager()


# Patch LLMService.generate for llm_executor ----------------------------------


class _StubLLMService:  # pylint: disable=too-few-public-methods
    async def generate(
        self,
        *_,  # ignore positional
        **__,  # ignore keyword
    ) -> tuple[str, None, None]:  # type: ignore[override]
        return "Hi there!", None, None


@pytest.mark.asyncio
async def test_llm_executor_stubbed(monkeypatch):
    cfg = LLMOperatorConfig(
        id="llm1",
        type="llm",
        model="gpt-4o",
        prompt="Hello",
        llm_config=LLMConfig(provider=ModelProvider.OPENAI),
    )

    # Monkey-patch LLMService inside executor module
    monkeypatch.setattr("ice_orchestrator.execution.executors.builtin.LLMService", _StubLLMService)

    result = await llm_executor(_StubChain(), cfg, {})  # type: ignore[arg-type]

    assert result.success is True
    assert result.output["text"] == "Hi there!"


@pytest.mark.asyncio
async def test_tool_executor_placeholder(monkeypatch):
    cfg = ToolNodeConfig(
        id="tool1",
        type="tool",
        tool_name="echo_tool",
        tool_args={"msg": "{foo}"},
        input_schema={"foo": "str"},
        output_schema={"msg": "str"},
    )

    ctx = {"foo": "bar"}

    out = await tool_executor(_StubChain(), cfg, ctx)  # type: ignore[arg-type]

    assert out.success is True
    assert out.output == {"name": "echo_tool", "args": {"msg": "bar"}}


@pytest.mark.asyncio
async def test_condition_executor_true_false():
    cfg_true = ConditionNodeConfig(id="c1", type="condition", expression="x > 3")
    cfg_false = ConditionNodeConfig(id="c2", type="condition", expression="x < 3")

    ctx = {"x": 5}

    res_true = await condition_executor(None, cfg_true, ctx)  # type: ignore[arg-type]
    res_false = await condition_executor(None, cfg_false, ctx)  # type: ignore[arg-type]

    assert res_true.output["result"] is True
    assert res_false.output["result"] is False 