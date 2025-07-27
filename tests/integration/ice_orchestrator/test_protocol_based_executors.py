"""Focused functional tests for protocol-based executor system.

These tests validate that the refactored executors properly use the registry
protocol instead of manual node instantiation, ensuring proper architecture
compliance and eliminating abstract method issues.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from typing import Any, Dict

from ice_core.models import (
    NodeExecutionResult, NodeMetadata, NodeType,
    ToolNodeConfig, LLMOperatorConfig as LLMNodeConfig
)
from ice_core.protocols.workflow import ScriptChainLike
from ice_core.unified_registry import registry
from ice_orchestrator.execution.executors.unified import (
    tool_executor, llm_executor
)


class MockTool:
    """Mock tool that implements ITool protocol."""
    
    def __init__(self, expected_output: Dict[str, Any]):
        self.expected_output = expected_output
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock execution that returns predefined output."""
        return self.expected_output
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {"type": "object", "properties": {"file_path": {"type": "string"}}}
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        return {"type": "object", "properties": {"rows": {"type": "array"}}}


class MockChain:
    """Mock chain implementing ScriptChainLike protocol."""
    
    def __init__(self):
        self.context_manager = Mock()
        self._agent_cache = {}
        self._chain_tools = []


class TestProtocolBasedToolExecutor:
    """Test tool executor using ITool protocol via registry."""
    
    @pytest.fixture
    def mock_chain(self):
        return MockChain()
    
    @pytest.fixture
    def tool_config(self):
        return ToolNodeConfig(
            id="test_tool",
            name="Test CSV Reader",
            tool_name="csv_reader",
            tool_args={"file_path": "/data/test.csv"},
            input_schema={"file_path": "str"},
            output_schema={"rows": "list[dict]", "headers": "list[str]"}
        )
    
    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Setup mock tool in registry before each test."""
        # Create mock tool
        mock_tool = MockTool({"rows": [{"col1": "val1"}], "headers": ["col1"]})
        
        # Register it in the registry
        registry.register_instance(NodeType.TOOL, "csv_reader", mock_tool)
        
        yield
        
        # Clean up after test
        try:
            del registry._instances[NodeType.TOOL]["csv_reader"]
        except (KeyError, AttributeError):
            pass
    
    async def test_tool_executor_uses_registry_lookup(self, mock_chain, tool_config):
        """Test that tool executor uses registry lookup instead of manual instantiation."""
        context = {"additional_data": "test"}
        
        # Execute tool
        result = await tool_executor(mock_chain, tool_config, context)
        
        # Verify successful execution
        assert result.success is True
        assert result.error is None
        assert result.output == {"rows": [{"col1": "val1"}], "headers": ["col1"]}
        
        # Verify metadata is properly set
        assert result.metadata.node_id == "test_tool"
        assert result.metadata.node_type == "tool"
        assert result.metadata.name == "Test CSV Reader"
        assert isinstance(result.execution_time, float)
        assert result.execution_time > 0
    
    async def test_tool_executor_merges_config_and_context(self, mock_chain, tool_config):
        """Test that tool executor properly merges tool_args with runtime context."""
        # Mock tool that echoes its inputs
        echo_tool = Mock()
        echo_tool.execute = AsyncMock(return_value={"echoed": "inputs"})
        
        registry.register_instance(NodeType.TOOL, "csv_reader", echo_tool)
        
        context = {"runtime_param": "runtime_value"}
        
        # Execute tool
        result = await tool_executor(mock_chain, tool_config, context)
        
        # Verify tool was called with merged inputs
        expected_inputs = {
            "file_path": "/data/test.csv",  # from tool_args
            "runtime_param": "runtime_value"  # from context
        }
        echo_tool.execute.assert_called_once_with(expected_inputs)
    
    async def test_tool_executor_handles_missing_tool(self, mock_chain):
        """Test error handling when tool is not found in registry."""
        config = ToolNodeConfig(
            id="missing_tool",
            name="Missing Tool",
            tool_name="nonexistent_tool",
            tool_args={},
            input_schema={},
            output_schema={}
        )
        
        # Execute with missing tool
        result = await tool_executor(mock_chain, config, {})
        
        # Verify failure
        assert result.success is False
        assert "nonexistent_tool" in result.error
        assert result.output == {}
        assert result.metadata.error_type is not None


class TestProtocolBasedLLMExecutor:
    """Test LLM executor using LLM service directly."""
    
    @pytest.fixture
    def mock_chain(self):
        return MockChain()
    
    @pytest.fixture
    def llm_config(self):
        from ice_core.models.llm import LLMConfig
        from ice_core.models.enums import ModelProvider
        
        return LLMNodeConfig(
            id="test_llm",
            name="Test Analyzer",
            model="gpt-4-turbo",
            prompt="Analyze this data: {data}",  # Changed from prompt_template
            temperature=0.7,
            max_tokens=500,
            llm_config=LLMConfig(provider=ModelProvider.OPENAI)  # Added required field
        )
    
    @pytest.fixture(autouse=True)
    def mock_llm_service(self, monkeypatch):
        """Mock the LLM service for testing."""
        mock_service = Mock()
        mock_service.generate = AsyncMock(return_value=(
            "This is a test analysis.", 
            {"prompt_tokens": 20, "completion_tokens": 5}, 
            None
        ))
        
        # Mock the import and instantiation
        def mock_llm_service_init():
            return mock_service
        
        # Mock the import inside the module
        import ice_orchestrator.providers.llm_service
        monkeypatch.setattr(
            ice_orchestrator.providers.llm_service,
            "LLMService",
            mock_llm_service_init
        )
        
        return mock_service
    
    async def test_llm_executor_uses_service_directly(self, mock_chain, llm_config, mock_llm_service):
        """Test that LLM executor uses LLM service directly."""
        context = {"data": "sample data"}
        
        # Execute LLM
        result = await llm_executor(mock_chain, llm_config, context)
        
        # Verify successful execution
        assert result.success is True
        assert result.error is None
        assert result.output == {"text": "This is a test analysis."}
        
        # Verify LLM service was called
        mock_llm_service.generate.assert_called_once()
        call_args = mock_llm_service.generate.call_args
        
        # Check LLM config
        llm_config_arg = call_args[1]["llm_config"]
        assert llm_config_arg.model == "gpt-4-turbo"
        assert llm_config_arg.temperature == 0.7
        assert llm_config_arg.max_tokens == 500
        assert llm_config_arg.provider == "openai"
        
        # Check prompt was rendered
        prompt_arg = call_args[1]["prompt"]
        assert prompt_arg == "Analyze this data: sample data"
    
    async def test_llm_executor_handles_missing_template_vars(self, mock_chain, llm_config, mock_llm_service):
        """Test error handling when template variables are missing."""
        context = {}  # Missing 'data' variable
        
        # Execute LLM
        result = await llm_executor(mock_chain, llm_config, context)
        
        # Verify failure
        assert result.success is False
        assert "Missing template variable" in result.error
        assert "data" in result.error
        assert result.output == {}
    
    async def test_llm_executor_handles_json_response_format(self, mock_chain, llm_config, mock_llm_service):
        """Test JSON response format parsing."""
        # Configure for JSON output
        llm_config.response_format = {"type": "json_object"}
        
        # Mock JSON response
        mock_llm_service.generate.return_value = (
            '{"analysis": "test", "score": 95}',
            {"prompt_tokens": 20, "completion_tokens": 10},
            None
        )
        
        context = {"data": "test data"}
        
        # Execute LLM
        result = await llm_executor(mock_chain, llm_config, context)
        
        # Verify JSON parsing
        assert result.success is True
        assert result.output == {"analysis": "test", "score": 95}
    
    async def test_llm_executor_handles_llm_service_error(self, mock_chain, llm_config, mock_llm_service):
        """Test error handling when LLM service returns an error."""
        # Mock service error
        mock_llm_service.generate.return_value = (
            None,
            None,
            "API key invalid"
        )
        
        context = {"data": "test data"}
        
        # Execute LLM
        result = await llm_executor(mock_chain, llm_config, context)
        
        # Verify failure
        assert result.success is False
        assert "LLM service error: API key invalid" in result.error
        assert result.output == {}


class TestProtocolBasedArchitecture:
    """Integration tests for protocol-based architecture compliance."""
    
    def test_executors_use_registry_protocol(self):
        """Test that executors follow the IRegistry protocol pattern."""
        from ice_orchestrator.execution.executors.unified import tool_executor, llm_executor
        import inspect
        
        # Check tool executor source for registry usage
        tool_source = inspect.getsource(tool_executor)
        assert "registry.get_instance" in tool_source
        assert "NodeType.TOOL" in tool_source
        assert "ToolNode(" not in tool_source  # Should not manually instantiate
        
        # Check LLM executor source for service usage
        llm_source = inspect.getsource(llm_executor)
        assert "LLMService" in llm_source
        assert "LLMNode(" not in llm_source  # Should not manually instantiate
    
    def test_no_abstract_method_issues(self):
        """Test that we don't have abstract method instantiation issues."""
        # This test passes if import doesn't raise abstract method errors
        from ice_orchestrator.execution.executors.unified import (
            tool_executor, llm_executor, condition_executor,
            agent_executor
            # workflow_executor not implemented yet
        )
        
        # All executors should be callable functions
        assert callable(tool_executor)
        assert callable(llm_executor)
        assert callable(condition_executor)
        assert callable(agent_executor)
        # workflow_executor not implemented yet
    
    def test_registry_integration(self):
        """Test that registry integration works as expected."""
        from ice_core.unified_registry import registry
        from ice_core.models.enums import NodeType
        
        # Test tool registration and retrieval
        mock_tool = Mock()
        registry.register_instance(NodeType.TOOL, "test_tool", mock_tool)
        
        retrieved_tool = registry.get_instance(NodeType.TOOL, "test_tool")
        assert retrieved_tool is mock_tool
        
        # Clean up
        del registry._instances[NodeType.TOOL]["test_tool"] 