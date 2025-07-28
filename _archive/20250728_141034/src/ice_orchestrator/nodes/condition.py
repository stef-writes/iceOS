"""Condition node - branching logic."""
from typing import Dict, Any, List
from ice_core.base_node import BaseNode

class ConditionNode(BaseNode):
    """Branching node that decides execution path based on expression."""
    
    expression: str
    true_nodes: List[str] = []
    false_nodes: List[str] = []
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "result": {"type": "boolean"},
                "branch": {"type": "string", "enum": ["true", "false"]}
            },
            "required": ["result", "branch"]
        }
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate expression and return branch decision."""
        # Safe evaluation of boolean expression
        try:
            # Create safe evaluation context
            safe_dict = {"__builtins__": {}}
            safe_dict.update(inputs)
            
            # Evaluate expression
            result = bool(eval(self.expression, safe_dict))
            
            return {
                "result": result,
                "branch": "true" if result else "false"
            }
        except Exception as e:
            raise ValueError(f"Failed to evaluate condition '{self.expression}': {e}") 