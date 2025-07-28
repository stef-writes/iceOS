"""Monitor node - real-time workflow monitoring."""
from typing import Dict, Any
from ice_core.base_node import BaseNode
from ice_core.models.node_models import MonitorNodeConfig

class MonitorNode(BaseNode):
    """Real-time monitoring node with alerting and control actions."""
    
    config: MonitorNodeConfig
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "monitoring_active": {"type": "boolean"},
                "checks_performed": {"type": "integer"},
                "triggers_fired": {"type": "integer"},
                "alerts_sent": {"type": "integer"},
                "action_taken": {"type": "string"},
                "final_status": {"type": "string"}
            },
            "required": ["monitoring_active", "checks_performed", "action_taken"]
        }
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "monitoring_context": {
                    "type": "object",
                    "description": "Context data for metric evaluation"
                },
                "workflow_metrics": {
                    "type": "object",
                    "description": "Current workflow metrics (cost, latency, etc.)"
                }
            }
        }
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute monitoring through metrics evaluator."""
        from .metrics import MetricsEvaluator
        
        # Create metrics evaluator with our configuration
        evaluator = MetricsEvaluator(self.config)
        
        # Execute monitoring
        result = await evaluator.monitor(inputs)
        
        return result.to_dict() 