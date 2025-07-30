"""Tests for WorkflowExecutionService."""
import pytest
from typing import Dict, Any
from ice_core.models.mcp import NodeSpec
from ice_core.models.node_models import ToolNodeConfig
from ice_orchestrator.services.workflow_execution_service import WorkflowExecutionService
from ice_orchestrator.workflow import Workflow


class MockToolExecutor:
    """Mock tool executor for testing."""
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return {"result": "success", "args": kwargs}


@pytest.mark.asyncio
async def test_execute_blueprint_with_node_specs():
    """Test executing a blueprint with NodeSpec objects."""
    # Create test NodeSpec
    node_spec = NodeSpec(
        id="test_tool",
        type="tool",
        tool_name="mock_tool",
        tool_args={"param": "value"},
        input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"result": {"type": "string"}}}
    )
    
    service = WorkflowExecutionService()
    
    # Mock the tool execution
    from ice_core.unified_registry import registry
    from ice_core.models.enums import NodeType
    
    # Register mock tool
    original_get = registry.get_instance
    def mock_get(node_type, name):
        if node_type == NodeType.TOOL and name == "mock_tool":
            return MockToolExecutor()
        return original_get(node_type, name)
    
    registry.get_instance = mock_get
    
    try:
        # Execute blueprint
        result = await service.execute_blueprint(
            [node_spec],
            inputs={"test": "data"},
            name="test_workflow"
        )
        
        # Verify execution
        assert isinstance(result, dict)
        # Result structure depends on Workflow.execute() implementation
        
    finally:
        registry.get_instance = original_get


@pytest.mark.asyncio
async def test_execute_workflow_with_instance():
    """Test executing a ready Workflow instance."""
    # Create workflow with tool node
    tool_config = ToolNodeConfig(
        id="test_tool",
        type="tool",
        tool_name="mock_tool",
        tool_args={"param": "value"},
        input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"result": {"type": "string"}}}
    )
    
    workflow = Workflow(
        nodes=[tool_config],
        name="test_workflow"
    )
    
    service = WorkflowExecutionService()
    
    # Mock the tool execution
    from ice_core.unified_registry import registry
    from ice_core.models.enums import NodeType
    
    # Register mock tool
    original_get = registry.get_instance
    def mock_get(node_type, name):
        if node_type == NodeType.TOOL and name == "mock_tool":
            return MockToolExecutor()
        return original_get(node_type, name)
    
    registry.get_instance = mock_get
    
    try:
        # Execute workflow
        result = await service.execute_workflow(
            workflow,
            inputs={"test": "data"}
        )
        
        # Verify execution
        assert isinstance(result, dict)
        
        # Verify inputs were injected
        ctx = workflow.context_manager.get_context(session_id="run")
        assert ctx is not None
        assert ctx.metadata.get("inputs") == {"test": "data"}
        
    finally:
        registry.get_instance = original_get


@pytest.mark.asyncio
async def test_execute_workflow_builder():
    """Test executing from a WorkflowBuilder."""
    from ice_sdk.builders.workflow import WorkflowBuilder
    
    # Create builder
    builder = WorkflowBuilder("test_workflow")
    builder.add_tool("test_tool", "mock_tool", param="value")
    
    service = WorkflowExecutionService()
    
    # Mock the tool execution
    from ice_core.unified_registry import registry
    from ice_core.models.enums import NodeType
    
    # Register mock tool
    original_get = registry.get_instance
    def mock_get(node_type, name):
        if node_type == NodeType.TOOL and name == "mock_tool":
            return MockToolExecutor()
        return original_get(node_type, name)
    
    registry.get_instance = mock_get
    
    try:
        # Execute from builder
        result = await service.execute_workflow_builder(
            builder,
            inputs={"test": "data"}
        )
        
        # Verify execution
        assert isinstance(result, dict)
        
    finally:
        registry.get_instance = original_get


def test_type_safety():
    """Test that incorrect types raise errors."""
    service = WorkflowExecutionService()
    
    # Test execute_workflow with wrong type should fail type checking
    # This would be caught by mypy --strict
    # with pytest.raises(TypeError):
    #     await service.execute_workflow({"foo": "bar"})  # type: ignore[arg-type]
    
    # Test execute_blueprint with wrong type
    # with pytest.raises(TypeError):
    #     await service.execute_blueprint("not a list")  # type: ignore[arg-type]
    
    # For runtime, we can test that NodeSpec validation works
    with pytest.raises(Exception):  # Pydantic validation error
        bad_spec = {"id": "bad", "type": "invalid_type"}
        NodeSpec(**bad_spec)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])