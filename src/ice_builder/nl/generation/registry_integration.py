"""Integration with iceOS unified registry for tools and agents.

This module provides utilities to query available tools, agents, and toolkits
from the registry to inform blueprint generation decisions.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ice_core.unified_registry import registry as global_registry


class RegistryIntegration:
    """Provides access to registered components for blueprint generation."""
    
    def __init__(self) -> None:
        """Initialize registry integration."""
        self.registry = global_registry
    
    def get_available_tools(self) -> Dict[str, str]:
        """Get all available tools with descriptions.
        
        Returns:
            Dictionary mapping tool names to descriptions.
        """
        tools = {}
        for tool_name in self.registry.list_tools():
            try:
                tool = self.registry.get_tool(tool_name)
                if hasattr(tool, "description"):
                    tools[tool_name] = tool.description
                else:
                    tools[tool_name] = f"Tool: {tool_name}"
            except Exception:
                # Skip tools that can't be loaded
                continue
        
        return tools
    
    def get_available_agents(self) -> List[str]:
        """Get all available agent names.
        
        Returns:
            List of registered agent names.
        """
        return self.registry.list_agents()
    
    def suggest_tools_for_task(self, task_description: str) -> List[str]:
        """Suggest relevant tools based on task description.
        
        Args:
            task_description: Natural language task description.
            
        Returns:
            List of suggested tool names.
        """
        suggestions = []
        task_lower = task_description.lower()
        
        # Tool keyword mappings
        tool_keywords = {
            "csv_reader": ["csv", "spreadsheet", "excel", "table"],
            "json_processor": ["json", "api response", "data extraction"],
            "file_writer": ["save", "write", "export", "output file"],
            "web_scraper": ["web", "scrape", "crawl", "website"],
            "database_query": ["database", "sql", "query", "fetch data"],
            "email_sender": ["email", "send", "notify", "alert"],
            "pdf_reader": ["pdf", "document", "extract text"],
            "image_processor": ["image", "photo", "resize", "convert"],
        }
        
        # Check available tools against keywords
        available_tools = self.get_available_tools()
        
        for tool_name in available_tools:
            # Direct name match
            if tool_name in task_lower:
                suggestions.append(tool_name)
                continue
            
            # Keyword match
            if tool_name in tool_keywords:
                if any(keyword in task_lower for keyword in tool_keywords[tool_name]):
                    suggestions.append(tool_name)
        
        return list(set(suggestions))  # Remove duplicates
    
    def can_create_custom_tool(self, tool_spec: Dict[str, Any]) -> bool:
        """Check if a custom tool can be created based on spec.
        
        Args:
            tool_spec: Tool specification with name, inputs, outputs.
            
        Returns:
            True if the tool can be created.
        """
        # Check required fields
        required_fields = ["name", "description", "inputs", "outputs"]
        if not all(field in tool_spec for field in required_fields):
            return False
        
        # Check name conflicts
        if self.registry.has_tool(tool_spec["name"]):
            return False
        
        # Basic validation passed
        return True
    
    def generate_tool_creation_code(self, tool_spec: Dict[str, Any]) -> str:
        """Generate code to create a custom tool.
        
        Args:
            tool_spec: Tool specification.
            
        Returns:
            Python code for tool creation.
        """
        template = '''from ice_core.base_tool import ToolBase
from typing import Dict, Any


class {class_name}(ToolBase):
    """Custom tool: {description}"""
    
    name = "{tool_name}"
    description = "{description}"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the tool.
        
        Args:
            {input_args}
            
        Returns:
            Dictionary with:
            {output_fields}
        """
        # TODO: Implement tool logic
        result = {{}}
        
        {processing_logic}
        
        return result


# Register the tool
from ice_core.unified_registry import registry
registry.register_instance(
    NodeType.TOOL,
    "{tool_name}",
    {class_name}(),
)'''
        
        # Generate class name
        class_name = "".join(word.capitalize() for word in tool_spec["name"].split("_"))
        
        # Format input args
        input_args = "\n            ".join(
            f"{inp['name']}: {inp.get('description', 'Input parameter')}"
            for inp in tool_spec.get("inputs", [])
        )
        
        # Format output fields
        output_fields = "\n            ".join(
            f"- {out['name']}: {out.get('description', 'Output value')}"
            for out in tool_spec.get("outputs", [])
        )
        
        # Generate basic processing logic
        processing_lines = []
        for output in tool_spec.get("outputs", []):
            processing_lines.append(f"result['{output['name']}'] = None  # TODO: Calculate {output['name']}")
        processing_logic = "\n        ".join(processing_lines)
        
        return template.format(
            class_name=class_name,
            tool_name=tool_spec["name"],
            description=tool_spec["description"],
            input_args=input_args or "No specific inputs",
            output_fields=output_fields or "- result: Processing result",
            processing_logic=processing_logic or "# TODO: Add processing logic",
        )