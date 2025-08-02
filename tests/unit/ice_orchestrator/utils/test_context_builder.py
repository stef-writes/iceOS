import pytest

from ice_core.exceptions import CoreError
from ice_core.models.node_models import (
    NodeExecutionResult,
    NodeMetadata,
    ToolNodeConfig,
)
from ice_orchestrator.utils.context_builder import ContextBuilder

pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
async def test_context_builder_success():
    # Dependency node result ---------------------------------------------
    from datetime import datetime

    dep_result = NodeExecutionResult(
        success=True,
        output={"stats": {"count": 10}},
        metadata=NodeMetadata(
            node_id="dep",
            node_type="tool",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
        ),
    )

    # Node with mapping ---------------------------------------------------
    node = ToolNodeConfig(
        id="n2",
        type="tool",
        tool_name="noop",
        tool_args={},
        input_schema={},
        output_schema={},
        input_mappings={
            "total": {"source_node_id": "dep", "source_output_key": "stats.count"}
        },
    )

    ctx = ContextBuilder.build_node_context(node, {"dep": dep_result})
    assert ctx == {"total": 10}


@pytest.mark.asyncio
async def test_context_builder_missing_dep_raises():
    node = ToolNodeConfig(
        id="n3",
        type="tool",
        tool_name="noop",
        tool_args={},
        input_schema={},
        output_schema={},
        input_mappings={"x": {"source_node_id": "missing", "source_output_key": "foo"}},
    )

    with pytest.raises(CoreError):
        _ = ContextBuilder.build_node_context(node, {}) 