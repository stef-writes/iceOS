"""Decorators for the new node system."""
import functools
import inspect
from typing import Any, Callable, Optional, Type, Dict
from pathlib import Path

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType


def tool(
    name: Optional[str] = None,
    auto_register: bool = True,
    auto_generate_tests: bool = False,
    test_output_dir: Optional[Path] = None,
    marketplace_metadata: Optional[Dict[str, Any]] = None,
) -> Callable[[Type[ToolBase]], Type[ToolBase]]:
    """Enhanced decorator for tool classes with auto-registration and test generation.
    
    Args:
        name: Tool name for registry (defaults to class name)
        auto_register: Automatically register in unified registry
        auto_generate_tests: Generate test scaffolding
        test_output_dir: Where to write generated tests
        marketplace_metadata: Future marketplace integration metadata
        
    Example:
        @tool(auto_generate_tests=True)
        class CSVReaderTool(ToolBase):
            '''Reads and parses CSV files.'''
            
            async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                file_path = input_data['file_path']
                # ... implementation
    """
    def decorator(cls: Type[ToolBase]) -> Type[ToolBase]:
        # Validate it's a proper tool
        if not issubclass(cls, ToolBase):
            raise TypeError(f"{cls.__name__} must inherit from ToolBase")
            
        # Extract tool name
        tool_name = name or cls.__name__.replace('Tool', '').lower()
        
        # Auto-generate schema methods if not present
        if not hasattr(cls, 'get_input_schema') or _is_default_method(cls.get_input_schema):
            cls.get_input_schema = classmethod(_generate_input_schema(cls))
            
        if not hasattr(cls, 'get_output_schema') or _is_default_method(cls.get_output_schema):
            cls.get_output_schema = classmethod(_generate_output_schema(cls))
        
        # Add metadata
        cls._tool_metadata = {
            'name': tool_name,
            'description': cls.__doc__ or f"{cls.__name__} tool",
            'marketplace': marketplace_metadata or {},
            'auto_generated_schemas': True
        }
        
        # Auto-register if requested
        if auto_register:
            # Create an instance for registration
            tool_instance = cls()
            registry.register_instance(NodeType.TOOL, tool_name, tool_instance)
            
        # Generate test scaffolding if requested
        if auto_generate_tests:
            _generate_test_file(cls, tool_name, test_output_dir)
            
        return cls
        
    return decorator


def _is_default_method(method: Any) -> bool:
    """Check if method is inherited from ToolBase without override."""
    # Simple check - in real implementation would be more robust
    return 'ToolBase' in str(method)


def _generate_input_schema(cls: Type[ToolBase]) -> Callable:
    """Generate input schema by introspecting execute method."""
    def get_input_schema(cls_ref) -> Dict[str, Any]:
        # Inspect _execute_impl method signature
        sig = inspect.signature(cls._execute_impl)
        
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Extract from execute method
        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'kwargs']:
                continue
                
            # Try to infer type from annotations
            if param.annotation != inspect.Parameter.empty:
                schema["properties"][param_name] = _type_to_schema(param.annotation)
                
            # Check if required
            if param.default == inspect.Parameter.empty:
                schema["required"].append(param_name)
                
        # If _execute_impl expects kwargs, try to parse docstring
        if 'kwargs' in sig.parameters:
            # Parse docstring for parameter descriptions
            docstring_schema = _parse_docstring_schema(cls.__doc__)
            schema["properties"].update(docstring_schema.get("properties", {}))
            schema["required"].extend(docstring_schema.get("required", []))
            
        return schema
        
    return get_input_schema


def _generate_output_schema(cls: Type[ToolBase]) -> Callable:
    """Generate output schema from docstring or return type annotation."""
    def get_output_schema(cls_ref) -> Dict[str, Any]:
        # Try return type annotation first
        sig = inspect.signature(cls._execute_impl)
        if sig.return_annotation != inspect.Parameter.empty:
            return _type_to_schema(sig.return_annotation)
            
        # Fall back to docstring parsing
        return _parse_docstring_schema(cls.__doc__, section="Returns")
        
    return get_output_schema


def _type_to_schema(python_type: Type) -> Dict[str, Any]:
    """Convert Python type to JSON schema."""
    # Simplified - real implementation would handle more types
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    
    # Handle Dict[str, Any] and similar
    if hasattr(python_type, '__origin__'):
        origin = python_type.__origin__
        return type_map.get(origin, {"type": "object"})
        
    return type_map.get(python_type, {"type": "object"})


def _parse_docstring_schema(docstring: Optional[str], section: str = "Args") -> Dict[str, Any]:
    """Parse schema from docstring - simplified version."""
    if not docstring:
        return {"type": "object", "properties": {}, "required": []}
        
    # This is a placeholder - real implementation would use docstring parsing
    # For now, return a basic schema
    return {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file"}
        },
        "required": ["file_path"]
    }


def _generate_test_file(cls: Type[ToolBase], tool_name: str, output_dir: Optional[Path]) -> None:
    """Generate test scaffolding for the tool."""
    output_dir = output_dir or Path("tests/unit/tools/")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = output_dir / f"test_{tool_name}.py"
    
    test_content = f'''"""Tests for {cls.__name__}."""
import pytest
from unittest.mock import Mock, patch
from {cls.__module__} import {cls.__name__}


class Test{cls.__name__}:
    """Test cases for {cls.__name__}."""
    
    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return {cls.__name__}()
    
    @pytest.fixture
    def sample_input(self):
        """Sample input for testing."""
        # TODO: Customize based on your tool's input schema
        return {{
            "file_path": "test.csv"
        }}
    
    async def test_execute_success(self, tool, sample_input):
        """Test successful execution."""
        # TODO: Add mocks for external dependencies
        result = await tool.execute(sample_input)
        
        assert result["success"] is True
        # TODO: Add more specific assertions
    
    async def test_execute_missing_required_field(self, tool):
        """Test execution with missing required field."""
        with pytest.raises(ValueError):
            await tool.execute({{}})
    
    def test_input_schema(self, tool):
        """Test input schema generation."""
        schema = tool.get_input_schema()
        
        assert schema["type"] == "object"
        assert "properties" in schema
        # TODO: Add specific schema checks
    
    def test_output_schema(self, tool):
        """Test output schema generation."""
        schema = tool.get_output_schema()
        
        assert schema["type"] == "object"
        # TODO: Add specific schema checks
'''
    
    # Only write if file doesn't exist
    if not test_file.exists():
        test_file.write_text(test_content)
        print(f"✅ Generated test file: {test_file}") 