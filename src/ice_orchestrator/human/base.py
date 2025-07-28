"""Human node - human-in-the-loop workflows."""
from typing import Dict, Any
from ice_core.base_node import BaseNode
from ice_core.models.node_models import HumanNodeConfig

class HumanNode(BaseNode):
    """Human interaction node for approval workflows and input collection."""
    
    config: HumanNodeConfig
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "approved": {"type": "boolean"},
                "response": {"type": "string"},
                "response_received": {"type": "boolean"},
                "timeout_occurred": {"type": "boolean"},
                "escalated": {"type": "boolean"}
            },
            "required": ["approved", "response_received"]
        }
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "context": {
                    "type": "object",
                    "description": "Context information for human decision making"
                },
                "user_id": {
                    "type": "string", 
                    "description": "ID of user who should respond"
                }
            }
        }
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute human interaction through approval handler."""
        from .approval import ApprovalHandler
        
        # Create approval handler with our configuration
        handler = ApprovalHandler(self.config)
        
        # Execute human interaction
        result = await handler.request_approval(inputs)
        
        return result.to_dict() 