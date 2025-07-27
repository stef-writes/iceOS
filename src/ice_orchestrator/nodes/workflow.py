"""Workflow node - reusable sub-workflows."""
from typing import Dict, Any
from ice_core.models import BaseNode

class WorkflowNode(BaseNode):
    """Execute a registered workflow as a node."""
    
    workflow_ref: str
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the referenced workflow."""
        from ice_core.unified_registry import registry
        from ice_core.models import NodeType
        
        # Get workflow instance
        workflow = registry.get_instance(NodeType.WORKFLOW, self.workflow_ref)
        
        # Execute workflow
        result = await workflow.execute(inputs)
        return result 