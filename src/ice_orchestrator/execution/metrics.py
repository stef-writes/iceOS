from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import BaseModel, Field

from ice_core.models.enums import NodeType

# NOTE: To avoid a heavy import chain, we import NodeExecutionResult lazily in update()
# to keep this utility lightweight and free from orchestrator dependencies at import time.

if TYPE_CHECKING:
    from ice_core.models.node_models import NodeExecutionResult

class ChainMetrics(BaseModel):
    """🚀 Enhanced metrics with nested structure by node type for better analytics."""

    total_tokens: int = 0
    total_cost: float = 0.0
    
    # 🚀 NESTED STRUCTURE: NodeType -> node_id -> metrics
    node_metrics: Dict[NodeType, Dict[str, Dict[str, Any]]] = Field(
        default_factory=dict
    )
    
    subdag_execution_time: float = 0.0

    def update(self, node_id: str, result: "NodeExecutionResult", node_type: NodeType = NodeType.TOOL) -> None:
        """🚀 Enhanced update with nested structure by node type.

        The method is intentionally tolerant: when *result.usage* is missing or
        incomplete the update becomes a no-op instead of raising, protecting the
        orchestrator from partial provider implementations.
        
        Args:
            node_id: The unique node identifier
            result: The execution result containing usage stats
            node_type: The type of node (tool, agent, etc.) for nested organization
        """

        usage = getattr(result, "usage", None)
        if not usage:
            return

        self.total_tokens += getattr(usage, "total_tokens", 0)
        # Support both historical *cost* and new *total_cost* field names.
        self.total_cost += getattr(usage, "total_cost", getattr(usage, "cost", 0.0))
        
        # 🚀 Store metrics in nested structure by node type
        try:
            self.node_metrics[node_type][node_id] = usage.model_dump()  # type: ignore[attr-defined]
        except Exception:
            # Fallback to dict() in case provider returns a plain object.
            self.node_metrics[node_type][node_id] = dict(usage) if isinstance(usage, dict) else {}

    def update_subdag_time(self, execution_time: float) -> None:
        """Update subDAG execution time metrics."""
        self.subdag_execution_time += execution_time
    
    # 🚀 NEW: High-performance analytics methods
    def get_metrics_by_node_type(self, node_type: NodeType) -> Dict[str, Dict[str, Any]]:
        """Get all metrics for a specific node type - perfect for monitoring!"""
        return dict(self.node_metrics.get(node_type, {}))
    
    def get_node_types_with_metrics(self) -> List[NodeType]:
        """List all node types that have metrics - great for dashboard!"""
        return list(self.node_metrics.keys())
    
    def get_total_cost_by_node_type(self, node_type: NodeType) -> float:
        """Calculate total cost for a specific node type - budget tracking!"""
        total = 0.0
        for node_metrics in self.node_metrics.get(node_type, {}).values():
            total += node_metrics.get("total_cost", node_metrics.get("cost", 0.0))
        return total
    
    def get_total_tokens_by_node_type(self, node_type: NodeType) -> int:
        """Calculate total tokens for a specific node type - usage monitoring!"""
        total = 0
        for node_metrics in self.node_metrics.get(node_type, {}).values():
            total += node_metrics.get("total_tokens", 0)
        return total
    
    def get_performance_summary(self) -> Dict[str, Dict[str, Any]]:
        """🚀 Get comprehensive performance summary by node type - ultimate analytics!"""
        summary = {}
        for node_type in self.get_node_types_with_metrics():
            type_metrics = self.get_metrics_by_node_type(node_type)
            summary[node_type.value] = {
                "node_count": len(type_metrics),
                "total_cost": self.get_total_cost_by_node_type(node_type),
                "total_tokens": self.get_total_tokens_by_node_type(node_type),
                "avg_cost_per_node": (
                    self.get_total_cost_by_node_type(node_type) / len(type_metrics)
                    if type_metrics else 0.0
                ),
                "nodes": list(type_metrics.keys())
            }
        return summary

    def as_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation suitable for JSON serialization."""

        return {
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "node_metrics": self.node_metrics,
            "subdag_execution_time": self.subdag_execution_time,
        }

# Global metric for SubDAG execution time
class SubDAGMetrics:
    """Global metrics for SubDAG execution tracking."""

    SUB_DAG_EXECUTION_TIME = 0.0

    @classmethod
    def record(cls, execution_time: float) -> None:
        """Record SubDAG execution time."""
        cls.SUB_DAG_EXECUTION_TIME += execution_time

    @classmethod
    def get_total_time(cls) -> float:
        """Get total SubDAG execution time."""
        return cls.SUB_DAG_EXECUTION_TIME
