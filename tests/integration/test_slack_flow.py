import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from ice_orchestrator.script_chain import ScriptChain, FailurePolicy
from ice_sdk.models.node_models import (
    AiNodeConfig,
    ToolNodeConfig,
    ConditionNodeConfig,
    NodeExecutionResult,
)
from ice_sdk.node_registry import NODE_REGISTRY
from ice_sdk.tools.base import function_tool, ToolContext, BaseTool

# Globals used by dummy slack tool
CALL_LOG: List[Dict[str, Any]] = []


@function_tool(name_override="slack_post")
async def _dummy_slack(ctx: ToolContext, channel: str, text: str) -> Dict[str, Any]:  # type: ignore[override]
    """Deterministic replacement for Slack tool; appends to CALL_LOG instead of hitting API."""
    CALL_LOG.append({"channel": channel, "text": text})
    return {"sent": True}


DUMMY_SLACK: BaseTool = _dummy_slack  # type: ignore[assignment]


async def _dummy_ai_executor(_, cfg: AiNodeConfig, __) -> NodeExecutionResult:  # type: ignore[override]
    """Return deterministic price based on marker in cfg.prompt."""
    from datetime import datetime
    from ice_sdk.models.node_models import NodeMetadata

    price = 67000.0 if "HIGH" in getattr(cfg, "prompt", "") else 65000.0
    meta = NodeMetadata(  # type: ignore[call-arg]
        node_id=cfg.id,
        node_type="ai",
        name=cfg.id,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
    )
    return NodeExecutionResult(  # type: ignore[call-arg]
        success=True,
        output={"price": price},
        metadata=meta,
    )


@pytest.mark.asyncio
async def test_flow_condition_triggers_slack(monkeypatch) -> None:
    """End-to-end run: price 67000 (>66000) should send Slack message."""

    spec_path = Path("examples/flows/slack_btc_alert.json")
    data = json.loads(spec_path.read_text())

    # Mark prompt so dummy executor returns HIGH price
    for n in data["nodes"]:
        if n["type"] == "ai":
            n["prompt"] += " HIGH"

    def _parse(d: Dict[str, Any]):
        if d["type"] == "ai":
            return AiNodeConfig.model_validate(d)
        if d["type"] == "tool":
            return ToolNodeConfig.model_validate(d)
        return ConditionNodeConfig.model_validate(d)

    nodes = [_parse(n) for n in data["nodes"]]

    # Patch ai executor
    original_ai = NODE_REGISTRY["ai"]
    NODE_REGISTRY["ai"] = _dummy_ai_executor  # type: ignore[assignment]
    CALL_LOG.clear()

    chain = ScriptChain(
        nodes=nodes,
        name="test_flow_high",
        tools=[DUMMY_SLACK],
        failure_policy=FailurePolicy.ALWAYS,
    )

    try:
        result = await chain.execute()
    finally:
        NODE_REGISTRY["ai"] = original_ai  # restore

    assert result.success is True
    assert len(CALL_LOG) == 1  # Slack fired


@pytest.mark.asyncio
async def test_flow_condition_blocks_slack(monkeypatch) -> None:
    """Price 65000 (<66000) should not send Slack message."""

    spec_path = Path("examples/flows/slack_btc_alert.json")
    data = json.loads(spec_path.read_text())

    # No HIGH marker → dummy price 65000
    def _parse(d: Dict[str, Any]):
        if d["type"] == "ai":
            return AiNodeConfig.model_validate(d)
        if d["type"] == "tool":
            return ToolNodeConfig.model_validate(d)
        return ConditionNodeConfig.model_validate(d)

    nodes = [_parse(n) for n in data["nodes"]]

    original_ai = NODE_REGISTRY["ai"]
    NODE_REGISTRY["ai"] = _dummy_ai_executor  # type: ignore[assignment]
    CALL_LOG.clear()

    chain = ScriptChain(
        nodes=nodes,
        name="test_flow_low",
        tools=[DUMMY_SLACK],
        failure_policy=FailurePolicy.ALWAYS,
    )

    try:
        result = await chain.execute()
    finally:
        NODE_REGISTRY["ai"] = original_ai

    assert result.success is True
    assert len(CALL_LOG) == 0  # Slack suppressed 