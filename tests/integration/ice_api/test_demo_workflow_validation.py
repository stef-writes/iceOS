"""End-to-end validation tests for the demo workflow.

This test validates the exact same workflow that the enhanced demo uses,
ensuring that the protocol-based refactor works correctly with real
tool registration and LLM service integration.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import httpx

from ice_core.models import (
    NodeType, ToolNodeConfig, LLMNodeConfig,
    NodeExecutionResult
)
from ice_core.models.mcp import RunRequest
from ice_sdk.unified_registry import registry
from ice_sdk.tools.system import CSVReaderTool
from ice_sdk.services.locator import ServiceLocator


class TestDemoWorkflowValidation:
    """Comprehensive validation of the enhanced demo workflow."""
    
    @pytest.fixture(autouse=True)
    def setup_services(self):
        """Setup services and tools exactly like the real application."""
        # Ensure CSV reader tool is registered (might already be from system __init__.py)
        try:
            registry.register_instance(NodeType.TOOL, "csv_reader", CSVReaderTool())
        except Exception:
            # Already registered, which is fine
            pass
        
        # Mock LLM service for testing
        mock_llm_service = Mock()
        mock_llm_service.generate = AsyncMock(return_value=(
            "This is a comprehensive analysis of the sales data...",
            {"prompt_tokens": 150, "completion_tokens": 50},
            None  # no error
        ))
        ServiceLocator.register("llm_service", mock_llm_service)
        
        yield
        
        # Cleanup
        ServiceLocator._services.clear()
    
    def test_tool_registration_validation(self):
        """Test that tools are properly registered and discoverable."""
        # Verify CSV reader is registered
        csv_tool = registry.get_instance(NodeType.TOOL, "csv_reader")
        assert csv_tool is not None
        assert hasattr(csv_tool, 'execute')
        assert callable(csv_tool.execute)
        
        # Verify it implements ITool protocol
        assert hasattr(csv_tool, 'get_input_schema')
        assert hasattr(csv_tool, 'get_output_schema')
        assert callable(csv_tool.get_input_schema)
        assert callable(csv_tool.get_output_schema)
    
    async def test_tool_executor_with_real_config(self):
        """Test tool executor with the exact config from the demo."""
        from ice_orchestrator.execution.executors.unified import tool_executor
        
        # Create exact config from demo
        tool_config = ToolNodeConfig(
            id="load_data",
            name="CSV Data Loader",
            tool_name="csv_reader",
            tool_args={"file_path": "data/sales_data.csv"},
            input_schema={"file_path": "str"},
            output_schema={"rows": "list[dict]", "headers": "list[str]"}
        )
        
        # Mock workflow (minimal implementation)
        mock_engine = Mock()
        mock_engine.context_manager = Mock()
        mock_engine._agent_cache = {}
        mock_engine._chain_tools = []
        
        # Create test CSV file content
        test_csv_content = "product,sales,region\nProduct A,1000,North\nProduct B,1500,South"
        
        # Mock the file operations for CSV reader
        from io import StringIO
        mock_file = StringIO(test_csv_content)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.open', return_value=mock_file):
            
            # Execute tool
            result = await tool_executor(mock_engine, tool_config, {})
            
            # Verify result structure
            assert isinstance(result, NodeExecutionResult)
            assert result.success is True
            assert result.error is None
            assert "rows" in result.output
            assert "headers" in result.output
            assert result.metadata.node_type == "tool"
            assert result.metadata.node_id == "load_data"
    
    async def test_llm_executor_with_real_config(self):
        """Test LLM executor with the exact config from the demo."""
        from ice_orchestrator.execution.executors.unified import llm_executor
        
        # Create exact config from demo
        llm_config = LLMNodeConfig(
            id="analyze_data",
            name="Data Analyzer",
            model="gpt-4-turbo-2024-04-09",  # Use allowed model name
            prompt_template="Analyze this sales data and provide insights: {rows}",
            temperature=0.7,
            max_tokens=500,
            provider="openai"
        )
        
        # Mock workflow
        mock_engine = Mock()
        mock_engine.context_manager = Mock()
        mock_engine._agent_cache = {}
        mock_engine._chain_tools = []
        
        # Context with data from previous step
        context = {
            "rows": [
                {"product": "Product A", "sales": "1000", "region": "North"},
                {"product": "Product B", "sales": "1500", "region": "South"}
            ]
        }
        
        # Execute LLM
        result = await llm_executor(mock_engine, llm_config, context)
        
        # Verify result structure
        assert isinstance(result, NodeExecutionResult)
        assert result.success is True
        assert result.error is None
        assert "text" in result.output
        assert result.metadata.node_type == "llm"
        assert result.metadata.node_id == "analyze_data"
        assert result.usage is not None
    
    def test_demo_blueprint_structure(self):
        """Test that the demo blueprint structure is valid."""
        # Exact blueprint structure from enhanced demo
        demo_blueprint = {
            "nodes": [
                {
                    "id": "load_data",
                    "type": "tool",
                    "name": "CSV Data Loader",
                    "tool_name": "csv_reader",
                    "tool_args": {"file_path": "data/sales_data.csv"},
                    "dependencies": [],
                    "input_schema": {"file_path": "str"},
                    "output_schema": {"rows": "list[dict]", "headers": "list[str]"}
                },
                {
                    "id": "analyze_data",
                    "type": "llm",
                    "name": "Data Analyzer",
                    "model": "gpt-4-turbo-2024-04-09",  # Use allowed model name
                    "prompt_template": "Analyze this sales data: {rows}",
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "dependencies": ["load_data"],
                    "input_schema": {"rows": "list[dict]"},
                    "output_schema": {"analysis": "dict"}
                }
            ]
        }
        
        # Validate node configurations can be created
        for node in demo_blueprint["nodes"]:
            if node["type"] == "tool":
                config = ToolNodeConfig(**node)
                assert config.tool_name == "csv_reader"
                assert config.type == "tool"
            elif node["type"] == "llm":
                config = LLMNodeConfig(**node)
                assert config.model == "gpt-4-turbo-2024-04-09"
                assert config.type == "llm"
    
    @pytest.mark.asyncio
    async def test_end_to_end_demo_simulation(self):
        """Simulate the complete demo workflow end-to-end."""
        from ice_orchestrator.execution.executors.unified import tool_executor, llm_executor
        
        # Setup mock workflow
        mock_engine = Mock()
        mock_engine.context_manager = Mock()
        mock_engine._agent_cache = {}
        mock_engine._chain_tools = []
        
        # Step 1: Tool execution (load_data)
        tool_config = ToolNodeConfig(
            id="load_data",
            name="CSV Data Loader",
            tool_name="csv_reader",
            tool_args={"file_path": "data/sales_data.csv"},
            input_schema={"file_path": "str"},
            output_schema={"rows": "list[dict]", "headers": "list[str]"}
        )
        
        test_csv_content = "product,sales,region\nProduct A,1000,North\nProduct B,1500,South"
        
        # Mock the file operations for CSV reader
        from io import StringIO
        mock_file = StringIO(test_csv_content)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.open', return_value=mock_file):
            
            tool_result = await tool_executor(mock_engine, tool_config, {})
            
            assert tool_result.success is True
            assert "rows" in tool_result.output
            data_rows = tool_result.output["rows"]
        
        # Step 2: LLM execution (analyze_data) using tool output
        llm_config = LLMNodeConfig(
            id="analyze_data",
            name="Data Analyzer",
            model="gpt-4-turbo-2024-04-09",  # Use allowed model name
            prompt_template="Analyze this sales data: {rows}",
            temperature=0.7,
            max_tokens=500,
            provider="openai"
        )
        
        # Use tool output as context for LLM
        llm_context = {"rows": data_rows}
        llm_result = await llm_executor(mock_engine, llm_config, llm_context)
        
        assert llm_result.success is True
        assert "text" in llm_result.output
        
        # Verify complete workflow success
        assert tool_result.metadata.duration > 0
        assert llm_result.metadata.duration > 0
        print(f"✅ End-to-end demo simulation successful!")
        print(f"   Tool execution: {tool_result.metadata.duration:.3f}s")
        print(f"   LLM execution: {llm_result.metadata.duration:.3f}s")
        print(f"   Data rows processed: {len(data_rows)}")
        print(f"   Analysis generated: {len(llm_result.output['text'])} chars")
    
    def test_api_payload_validation(self):
        """Test that the API payload structure matches what the demo sends."""
        # Exact payload structure from enhanced demo
        demo_payload = {
            "blueprint": {
                "blueprint_id": "enhanced_demo_test",
                "schema_version": "1.1.0",
                "nodes": [
                    {
                        "id": "load_data",
                        "type": "tool",
                        "name": "CSV Data Loader",
                        "tool_name": "csv_reader",
                        "tool_args": {"file_path": "data/sales_data.csv"},
                        "dependencies": [],
                        "input_schema": {"file_path": "str"},
                        "output_schema": {"rows": "list[dict]", "headers": "list[str]"}
                    }
                ],
                "metadata": {
                    "name": "Enhanced Demo Test",
                    "description": "Protocol-based demo validation",
                    "demo_type": "enhanced_real_llm",
                    "spatial_features_enabled": True
                }
            },
            "options": {
                "max_parallel": 3,
                "timeout_seconds": 300
            }
        }
        
        # Validate that RunRequest can parse this
        try:
            run_request = RunRequest(**demo_payload)
            assert run_request.blueprint.blueprint_id == "enhanced_demo_test"
            assert len(run_request.blueprint.nodes) == 1
            assert run_request.options.max_parallel == 3
        except Exception as e:
            pytest.fail(f"Demo payload validation failed: {e}")
    
    def test_error_handling_validation(self):
        """Test error handling scenarios that could break the demo."""
        from ice_orchestrator.execution.executors.unified import tool_executor
        
        # Test missing tool
        invalid_config = ToolNodeConfig(
            id="missing_tool",
            name="Missing Tool",
            tool_name="nonexistent_tool",
            tool_args={},
            input_schema={},
            output_schema={}
        )
        
        mock_engine = Mock()
        mock_engine.context_manager = Mock()
        mock_engine._agent_cache = {}
        mock_engine._chain_tools = []
        
        # Should handle gracefully without crashing
        async def test_missing_tool():
            result = await tool_executor(mock_engine, invalid_config, {})
            assert result.success is False
            assert "not found" in result.error.lower()
            assert result.metadata.error_type is not None
        
        asyncio.run(test_missing_tool())


if __name__ == "__main__":
    # Run a quick validation when called directly
    import sys
    
    print("🔍 Running demo workflow validation...")
    
    # Test tool registration
    registry.register_instance(NodeType.TOOL, "csv_reader", CSVReaderTool())
    csv_tool = registry.get_instance(NodeType.TOOL, "csv_reader")
    assert csv_tool is not None
    print("✅ Tool registration works")
    
    # Test config creation
    tool_config = ToolNodeConfig(
        id="test",
        name="Test", 
        tool_name="csv_reader",
        tool_args={},
        input_schema={},
        output_schema={}
    )
    assert tool_config.tool_name == "csv_reader"
    print("✅ Config creation works")
    
    print("🎉 Basic validation passed! Ready for demo.") 