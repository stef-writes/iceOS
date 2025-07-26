"""Integration tests for simplified tool creation pathways."""
import pytest
import tempfile
from pathlib import Path
import subprocess
import httpx
from typing import Dict, Any

from ice_core.base_tool import ToolBase
from ice_sdk.decorators import tool
from ice_sdk.unified_registry import registry
from ice_core.models.enums import NodeType


class TestToolCreationPathways:
    """Test all pathways for creating tools in iceOS."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    async def test_enhanced_decorator_pathway(self, temp_dir):
        """Test creating a tool with enhanced decorator."""
        # Clear registry
        if hasattr(registry, '_instances'):
            registry._instances[NodeType.TOOL] = {}
        
        # Create tool with all features
        @tool(
            name="enhanced_test",
            auto_register=True,
            auto_generate_tests=True,
            test_output_dir=temp_dir,
            marketplace_metadata={
                "category": "testing",
                "version": "1.0.0"
            }
        )
        class EnhancedTestTool(ToolBase):
            """A tool created with enhanced decorator."""
            
            async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                name: str = input_data["name"]
                return {"greeting": f"Hello, {name}!"}
        
        # Verify registration
        tool_instance = registry.get_instance(NodeType.TOOL, "enhanced_test")
        assert tool_instance is not None
        assert isinstance(tool_instance, EnhancedTestTool)
        
        # Verify test generation
        test_file = temp_dir / "test_enhanced_test.py"
        assert test_file.exists()
        assert "class TestEnhancedTestTool" in test_file.read_text()
        
        # Test execution
        result = await tool_instance.execute({"name": "World"})
        assert result["greeting"] == "Hello, World!"
        
        # Verify metadata
        assert hasattr(EnhancedTestTool, '_tool_metadata')
        assert EnhancedTestTool._tool_metadata['marketplace']['category'] == 'testing'
    
    def test_cli_scaffolding_pathway(self, temp_dir):
        """Test creating a tool via CLI scaffolding."""
        # This would test the CLI command
        # For now, test the underlying functions
        from ice_cli.commands.scaffold import _basic_tool_config, _generate_tool_code
        
        config = _basic_tool_config("cli_test_tool")
        assert config['name'] == 'cli_test_tool'
        assert config['class_name'] == 'CliTestToolTool'
        
        code = _generate_tool_code(config)
        assert '@tool(' in code
        assert 'class CliTestToolTool(ToolBase):' in code
        assert 'async def execute(self' in code
        
        # Write and verify
        tool_path = temp_dir / "cli_test_tool.py"
        tool_path.write_text(code)
        assert tool_path.exists()
    
    async def test_composition_pathway(self):
        """Test creating a tool through composition (API-based)."""
        # This would test the composition API
        # Mock the request/response for now
        from ice_api.api.tool_composer import _generate_composed_tool_code, ToolComposerRequest
        from ice_core.models.mcp import PartialBlueprint
        
        request = ToolComposerRequest(
            tool_name="composed_processor",
            description="Process and analyze data",
            nodes=[
                {
                    "id": "reader",
                    "type": "tool",
                    "config": {"tool_name": "csv_reader"}
                },
                {
                    "id": "analyzer", 
                    "type": "llm",
                    "config": {
                        "model": "gpt-3.5-turbo",
                        "prompt": "Analyze this data: {data}"
                    }
                }
            ],
            connections=[
                {"from_node": "reader", "to_node": "analyzer"}
            ],
            input_mapping={"file": "reader.file_path"},
            output_mapping={"analyzer.output": "analysis"}
        )
        
        partial = PartialBlueprint(
            blueprint_id="test_composition",
            description="Test composition"
        )
        
        code = _generate_composed_tool_code(request, partial)
        assert '@tool(name="composed_processor")' in code
        assert 'class ComposedProcessorTool(ToolBase):' in code
        assert 'self.builder = WorkflowBuilder' in code
    
    async def test_tool_discovery_and_usage(self):
        """Test that created tools can be discovered and used."""
        # Create a simple tool
        @tool(name="discoverable")
        class DiscoverableTool(ToolBase):
            async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"discovered": True}
        
        # List all tools
        all_tools = registry.list_nodes(NodeType.TOOL)
        assert "discoverable" in all_tools
        
        # Use through direct execution endpoint (simulated)
        tool_instance = registry.get_instance(NodeType.TOOL, "discoverable") 
        result = await tool_instance.execute({})
        assert result["discovered"] is True
    
    async def test_progressive_enhancement(self, temp_dir):
        """Test progressively enhancing a basic tool."""
        # Start with basic decorator
        @tool(name="basic", auto_register=False)
        class BasicTool(ToolBase):
            async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"basic": True}
        
        # Enhance with auto-generation
        @tool(
            name="enhanced",
            auto_register=False,
            auto_generate_tests=True,
            test_output_dir=temp_dir
        )
        class EnhancedTool(BasicTool):
            """Enhanced version with tests."""
            pass
        
        # Verify test was generated for enhanced version
        test_file = temp_dir / "test_enhanced.py"
        assert test_file.exists()
        
        # Both should work
        basic_result = await BasicTool().execute({})
        enhanced_result = await EnhancedTool().execute({})
        assert basic_result == enhanced_result == {"basic": True} 