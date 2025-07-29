from typing import Any, Dict, Optional
from unittest.mock import Mock, AsyncMock

import pytest

from ice_core.models.node_models import (
    LLMOperatorConfig,
    ToolNodeConfig,
    LLMConfig,
    AgentNodeConfig,
    WorkflowNodeConfig,
    ParallelNodeConfig,
    CodeNodeConfig,
)
from ice_core.models.enums import ModelProvider
from ice_orchestrator.execution.executors.unified import (
    llm_executor, tool_executor, agent_executor, workflow_executor, parallel_executor, code_executor
)

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
    _agent_cache = {}
    _chain_tools = []


# Patch LLMService.generate for llm_executor ----------------------------------


class _StubLLMService:  # pylint: disable=too-few-public-methods
    async def generate(
        self,
        *_,  # ignore positional
        **__,  # ignore keyword
    ) -> tuple[str, Optional[dict[str, int]], Optional[str]]:  # type: ignore[override]
        return "Hi there!", None, None


@pytest.mark.asyncio
async def test_llm_executor_stubbed(monkeypatch):
    """Test LLM executor returns response in correct format."""
    cfg = LLMOperatorConfig(
        id="llm1",
        type="llm",
        model="gpt-4o",
        prompt="Hello",
        llm_config=LLMConfig(provider=ModelProvider.OPENAI),
    )

    # Monkey-patch LLMService inside executor module
    monkeypatch.setattr("ice_orchestrator.providers.llm_service.LLMService", _StubLLMService)

    result = await llm_executor(_StubChain(), cfg, {})  # type: ignore[arg-type]

    assert result.success is True
    # Updated to match new output format
    assert result.output["response"] == "Hi there!"
    assert "prompt" in result.output
    assert "model" in result.output


@pytest.mark.asyncio
async def test_tool_executor_placeholder(monkeypatch):
    # For the protocol-based executor, we need to mock the registry
    from ice_core.unified_registry import registry
    from ice_core.models import NodeType
    
    # Create a mock tool
    mock_tool = Mock()
    mock_tool.execute = AsyncMock(return_value={"echoed": "bar"})
    
    # Register the mock tool
    registry.register_instance(NodeType.TOOL, "echo_tool", mock_tool)
    
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
    assert out.output == {"echoed": "bar"}
    
    # Clean up
    try:
        if NodeType.TOOL in registry._instances and "echo_tool" in registry._instances[NodeType.TOOL]:
            del registry._instances[NodeType.TOOL]["echo_tool"]
    except KeyError:
        # Already cleaned up
        pass


@pytest.mark.asyncio
async def test_agent_executor():
    """Test agent executor with mock agent."""
    from ice_core.unified_registry import registry
    from ice_core.models import NodeType
    
    # Create a mock agent
    mock_agent = Mock()
    mock_agent.execute = AsyncMock(return_value={"response": "Agent executed"})
    
    # Register the mock agent
    registry.register_instance(NodeType.AGENT, "test_agent", mock_agent)
    
    cfg = AgentNodeConfig(
        id="agent1",
        type="agent",
        package="test_agent",
        agent_config={"max_iterations": 5}
    )
    
    ctx = {"query": "test"}
    result = await agent_executor(_StubChain(), cfg, ctx)
    
    assert result.success is True
    # Just check the key parts - extra tracking fields are fine
    assert result.output["response"] == "Agent executed"
    assert result.output["agent_package"] == "test_agent"
    
    # Clean up
    try:
        if NodeType.AGENT in registry._instances and "test_agent" in registry._instances[NodeType.AGENT]:
            del registry._instances[NodeType.AGENT]["test_agent"]
    except KeyError:
        pass


@pytest.mark.asyncio
async def test_workflow_executor():
    """Test workflow executor with mock sub-workflow."""
    from ice_core.unified_registry import registry
    from ice_core.models import NodeType
    
    # Create a mock workflow
    mock_workflow = Mock()
    mock_workflow.execute = AsyncMock(return_value={"workflow_result": "completed"})
    
    # Register the mock workflow
    registry.register_instance(NodeType.WORKFLOW, "sub_workflow", mock_workflow)
    
    cfg = WorkflowNodeConfig(
        id="wf1",
        type="workflow",
        workflow_ref="sub_workflow",
        exposed_outputs={"result": "workflow_result"}
    )
    
    ctx = {"input": "test"}
    result = await workflow_executor(_StubChain(), cfg, ctx)
    
    assert result.success is True
    assert result.output == {"result": "completed"}
    
    # Clean up
    try:
        if NodeType.WORKFLOW in registry._instances and "sub_workflow" in registry._instances[NodeType.WORKFLOW]:
            del registry._instances[NodeType.WORKFLOW]["sub_workflow"]
    except KeyError:
        pass


@pytest.mark.asyncio
async def test_parallel_executor():
    """Test parallel executor with multiple branches."""
    cfg = ParallelNodeConfig(
        id="par1",
        type="parallel",
        branches=[["node1", "node2"], ["node3"]],
        merge_outputs=True
    )
    
    # Mock workflow that can execute nodes
    mock_workflow = Mock()
    async def mock_execute_node(node_id, ctx):
        return Mock(
            success=True,
            output={f"{node_id}_result": f"branch_{ctx['branch_index']}"}
        )
    mock_workflow.execute_node = mock_execute_node
    
    ctx = {"base": "context"}
    result = await parallel_executor(mock_workflow, cfg, ctx)
    
    assert result.success is True
    assert len(result.output["branch_results"]) == 2
    assert result.output["strategy"] == "all"  # Default strategy
    assert "merged" in result.output


@pytest.mark.asyncio
async def test_code_executor_syntax_error():
    """Test code executor with invalid syntax."""
    cfg = CodeNodeConfig(
        id="code2",
        type="code",
        code="invalid python syntax!!!",
        language="python"
    )
    
    result = await code_executor(_StubChain(), cfg, {})
    
    assert result.success is False
    assert "Invalid Python syntax" in result.error 