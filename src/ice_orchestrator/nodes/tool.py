"""Tool node - wraps registered tools."""
from typing import Dict, Any
from ice_core.models import BaseNode

class ToolNode(BaseNode):
    """Executes a registered tool."""
    
    tool_ref: str
    tool_args: Dict[str, Any] = {}
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the referenced tool."""
        from ice_sdk.unified_registry import registry
        from ice_core.models import NodeType
        
        # Get tool instance
        tool = registry.get_instance(NodeType.TOOL, self.tool_ref)
        
        # Merge static args with runtime inputs
        merged_args = {**self.tool_args, **inputs}
        
        # Execute tool
        if hasattr(tool, 'execute'):
            result = await tool.execute(merged_args)
        else:
            # Legacy tools might have _execute_impl
            result = await tool._execute_impl(**merged_args)
        
        return result if isinstance(result, dict) else {"result": result} 