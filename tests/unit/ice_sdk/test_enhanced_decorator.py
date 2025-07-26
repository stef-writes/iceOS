"""Test the enhanced @tool decorator."""
import pytest
from pathlib import Path
import tempfile
from typing import Dict, Any

from ice_core.base_tool import ToolBase
from ice_sdk.decorators import tool
from ice_sdk.unified_registry import registry
from ice_core.models.enums import NodeType


class TestEnhancedToolDecorator:
    """Test cases for enhanced @tool decorator."""
    
    def setup_method(self):
        """Clear registry before each test."""
        # Clear any existing tool registrations
        if hasattr(registry, '_instances'):
            registry._instances[NodeType.TOOL] = {}
    
    def test_basic_tool_registration(self):
        """Test basic tool registration with decorator."""
        @tool(name="test_tool")
        class TestTool(ToolBase):
            """A test tool."""
            async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
                return {"result": "success"}
        
        # Verify registration
        registered_tool = registry.get_instance(NodeType.TOOL, "test_tool")
        assert registered_tool is not None
        assert isinstance(registered_tool, TestTool)
    
    def test_auto_name_generation(self):
        """Test automatic name generation from class name."""
        @tool()
        class DataProcessorTool(ToolBase):
            """Process data."""
            async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
                return {"processed": True}
        
        # Should register as 'dataprocessor'
        registered_tool = registry.get_instance(NodeType.TOOL, "dataprocessor")
        assert registered_tool is not None
    
    def test_auto_schema_generation(self):
        """Test automatic schema generation."""
        @tool()
        class SchemaTestTool(ToolBase):
            """Test tool with auto-generated schemas.
            
            Args:
                file_path: Path to input file
                format: Optional format specification
            """
            async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
                file_path: str = kwargs["file_path"]
                format: str = kwargs.get("format", "csv")
                return {"file": file_path, "format": format}
        
        # Test schema generation
        input_schema = SchemaTestTool.get_input_schema()
        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        assert "file_path" in input_schema["properties"]
        
        output_schema = SchemaTestTool.get_output_schema()
        assert output_schema["type"] == "object"
    
    def test_metadata_attachment(self):
        """Test metadata is attached to tool class."""
        marketplace_meta = {
            "category": "data_processing",
            "tags": ["csv", "data"],
            "pricing": {"per_call": 0.001}
        }
        
        @tool(marketplace_metadata=marketplace_meta)
        class MetadataTool(ToolBase):
            """Tool with metadata."""
            async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
                return {}
        
        assert hasattr(MetadataTool, '_tool_metadata')
        assert MetadataTool._tool_metadata['marketplace'] == marketplace_meta
        assert MetadataTool._tool_metadata['name'] == 'metadata'
    
    def test_no_auto_register(self):
        """Test disabling auto-registration."""
        @tool(name="manual_tool", auto_register=False)
        class ManualTool(ToolBase):
            """Manually registered tool."""
            async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
                return {}
        
        # Should not be in registry
        from ice_sdk.unified_registry import RegistryError
        with pytest.raises(RegistryError):
            registry.get_instance(NodeType.TOOL, "manual_tool")
    
    def test_test_generation(self, tmp_path):
        """Test automatic test file generation."""
        test_dir = tmp_path / "tests"
        
        @tool(
            name="generator_test",
            auto_generate_tests=True,
            test_output_dir=test_dir
        )
        class GeneratorTestTool(ToolBase):
            """Tool that generates tests."""
            async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
                return {"generated": True}
        
        # Check test file was created
        test_file = test_dir / "test_generator_test.py"
        assert test_file.exists()
        
        # Verify test content
        content = test_file.read_text()
        assert "class TestGeneratorTestTool:" in content
        assert "async def test_execute_success" in content
        assert "def test_input_schema" in content
    
    def test_inheritance_validation(self):
        """Test that decorator validates ToolBase inheritance."""
        with pytest.raises(TypeError, match="must inherit from ToolBase"):
            @tool()
            class NotATool:
                """Not a proper tool."""
                pass
    
    @pytest.mark.asyncio
    async def test_decorated_tool_execution(self):
        """Test that decorated tools still execute properly."""
        @tool()
        class ExecutableTool(ToolBase):
            """Executable test tool."""
            async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
                value = kwargs.get("value", 0)
                return {"doubled": value * 2}
        
        tool_instance = ExecutableTool()
        result = await tool_instance.execute({"value": 21})
        assert result["doubled"] == 42 