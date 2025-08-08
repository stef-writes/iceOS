"""Decorators for the new node system."""

from typing import Callable, Optional, Type

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import register_tool_factory


def tool(
    name: Optional[str] = None,
    auto_register: bool = True,
    validate: bool = True,
) -> Callable[[Type[ToolBase]], Type[ToolBase]]:
    """Simple decorator for tool classes with auto-registration.

    Args:
        name: Tool name for registry (defaults to class name in snake_case)
        auto_register: Automatically register in unified registry
        validate: Whether to validate before registration (default: True)

    Example:
        @tool
        class CSVReaderTool(ToolBase):
            '''Reads and parses CSV files.'''

            async def _execute_impl(self, **kwargs):
                # ... implementation

        # Skip validation for testing
        @tool(validate=False)
        class TestTool(ToolBase):
            '''Test tool that might not pass validation.'''
    """

    def decorator(cls: Type[ToolBase]) -> Type[ToolBase]:
        # Validate it's a proper tool
        if not issubclass(cls, ToolBase):
            raise TypeError(f"{cls.__name__} must inherit from ToolBase")

        # Extract tool name - convert CamelCase to snake_case
        if name:
            tool_name = name
        else:
            # Convert "CSVReaderTool" -> "csv_reader"
            class_name = cls.__name__.replace("Tool", "")
            tool_name = "".join(
                [
                    "_" + c.lower() if c.isupper() and i > 0 else c.lower()
                    for i, c in enumerate(class_name)
                ]
            ).lstrip("_")

        # Auto-register a factory if requested
        if auto_register:
            # Expect a module-level factory named create_<tool_name>
            import_path = f"{cls.__module__}:create_{tool_name}"
            register_tool_factory(tool_name, import_path)

        return cls

    return decorator
