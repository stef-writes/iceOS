"""Unit node - stateless composition of other nodes."""
from typing import Dict, Any, List, Optional
from pydantic import Field
from ice_core.models import BaseNode
from ice_core.models import NodeConfig

class UnitNode(BaseNode):
    """Stateless composition of nodes into a mini-workflow."""
    
    # Either reference a registered unit or define inline
    unit_ref: Optional[str] = None
    nodes: List[NodeConfig] = Field(default_factory=list)
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the unit's internal workflow."""
        from ice_sdk.unified_registry import registry
        from ice_core.models import NodeType
        
        if self.unit_ref:
            # Get registered unit
            unit = registry.get_instance(NodeType.UNIT, self.unit_ref)
            return await unit.execute(inputs)
        else:
            # Execute inline nodes
            # This would use a mini-orchestrator
            from ice_orchestrator.mini_orchestrator import MiniOrchestrator
            
            orchestrator = MiniOrchestrator()
            result = await orchestrator.execute_dag(self.nodes, inputs)
            return result 