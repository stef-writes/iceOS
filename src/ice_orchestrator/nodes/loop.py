"""Loop node - iteration over collections."""
from typing import Dict, Any, List
from ice_core.models import BaseNode

class LoopNode(BaseNode):
    """Iterate over a collection and execute body nodes."""
    
    iterator_path: str
    body_nodes: List[str] = []
    max_iterations: int = 100
    
    @property

    
    def output_schema(self) -> Dict[str, Any]:

    
        return {
        "type": "object",
        "properties": {
            "results": {"type": "array"},
            "iterations": {"type": "integer"}
        },
        "required": ["results", "iterations"]
    }
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute loop over collection."""
        # Get the collection to iterate over
        collection = self._resolve_path(inputs, self.iterator_path)
        
        if not isinstance(collection, list):
            raise ValueError(f"Iterator path '{self.iterator_path}' must point to a list")
        
        results = []
        iterations = 0
        
        for item in collection[:self.max_iterations]:
            # Execute body nodes with current item
            # This would be handled by the orchestrator
            results.append(item)  # Placeholder
            iterations += 1
        
        return {
            "results": results,
            "iterations": iterations
        }
    
    def _resolve_path(self, data: Dict[str, Any], path: str) -> Any:
        """Resolve a dot-separated path in data."""
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Path '{path}' not found in data")
        
        return current 