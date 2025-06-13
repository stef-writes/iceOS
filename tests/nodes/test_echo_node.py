from __future__ import annotations

from typing import Any, Dict, Literal

import pytest

from ice_sdk.base_node import BaseNode
from ice_sdk.models.node_models import BaseNodeConfig, NodeExecutionResult, NodeMetadata


class EchoNodeConfig(BaseNodeConfig):
    """Config for EchoNode used in unit tests."""

    type: Literal["tool"] = "tool"
    input_schema: Dict[str, str] = {"text": "str"}
    output_schema: Dict[str, str] = {"text": "str"}


class EchoNode(BaseNode):
    """Simple node that echoes its input back as output."""

    async def execute(self, context: Dict[str, Any]) -> NodeExecutionResult:  # type: ignore[override]
        metadata = NodeMetadata(node_id=self.node_id, node_type="echo")  # type: ignore[arg-type]
        return NodeExecutionResult(success=True, output=context, metadata=metadata)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_echo_node_happy_path():
    cfg = EchoNodeConfig(id="echo1", name="Echo")
    node = EchoNode(cfg)

    ctx = {"text": "hello world"}

    # pre_execute should validate input and pass
    await node.pre_execute(ctx)

    result = await node.execute(ctx)
    assert result.success
    assert result.output == ctx


@pytest.mark.asyncio
async def test_echo_node_validation_error():
    cfg = EchoNodeConfig(id="echo2", name="Echo")
    node = EchoNode(cfg)

    bad_ctx = {"wrong": "field"}
    with pytest.raises(ValueError):
        await node.pre_execute(bad_ctx) 