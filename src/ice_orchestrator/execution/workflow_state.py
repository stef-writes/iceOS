"""Workflow execution state management.

Centralizes all runtime state for cleaner workflow execution logic.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ice_core.models import NodeExecutionResult
from ice_core.models.enums import NodeType


class ExecutionPhase(Enum):
    """Workflow execution phases for better observability."""
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    EXECUTING = "executing"
    LEVEL_EXECUTING = "level_executing"
    NODE_EXECUTING = "node_executing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LevelExecutionState:
    """State for a single execution level."""
    level_num: int
    node_ids: List[str]
    active_node_ids: List[str] = field(default_factory=list)
    # 🚀 NESTED STRUCTURE: NodeType -> node_id -> result
    results: Dict[NodeType, Dict[str, NodeExecutionResult]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    

@dataclass
class WorkflowExecutionState:
    """Centralized workflow execution state.
    
    This extracts all the runtime state management from the main Workflow class,
    making it easier to implement features like checkpointing, debugging, and
    incremental execution.
    """
    
    # Core execution state
    workflow_id: str
    workflow_name: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    phase: ExecutionPhase = ExecutionPhase.INITIALIZING
    
    # 🚀 NESTED RESULTS: NodeType -> node_id -> result for better analytics
    node_results: Dict[NodeType, Dict[str, NodeExecutionResult]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Execution tracking
    current_level: Optional[int] = None
    completed_levels: Set[int] = field(default_factory=set)
    executing_nodes: Set[str] = field(default_factory=set)
    completed_nodes: Set[str] = field(default_factory=set)
    failed_nodes: Set[str] = field(default_factory=set)
    skipped_nodes: Set[str] = field(default_factory=set)
    
    # Branch decisions from condition nodes
    branch_decisions: Dict[str, bool] = field(default_factory=dict)
    
    # Token/resource tracking
    total_tokens: int = 0
    total_cost: float = 0.0
    api_calls: int = 0
    
    # Checkpointing support
    checkpoint_enabled: bool = False
    last_checkpoint: Optional[datetime] = None
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    
    def record_node_start(self, node_id: str) -> None:
        """Record that a node has started executing."""
        self.executing_nodes.add(node_id)
        
    def record_node_complete(self, node_id: str, result: NodeExecutionResult) -> None:
        """Record node completion."""
        self.executing_nodes.discard(node_id)
        self.completed_nodes.add(node_id)
        from ice_core.models.enums import NodeType
        raw_type = getattr(result.metadata, 'node_type', None) if hasattr(result, 'metadata') and result.metadata else None
        try:
            node_type_enum = NodeType(str(raw_type)) if raw_type else NodeType.TOOL
        except ValueError:
            node_type_enum = NodeType.TOOL
        self.node_results[node_type_enum][node_id] = result
        
        if not result.success:
            self.failed_nodes.add(node_id)
            if result.error:
                self.errors.append(f"Node {node_id}: {result.error}")
                
    def record_node_skipped(self, node_id: str, reason: str) -> None:
        """Record that a node was skipped."""
        self.skipped_nodes.add(node_id)
        self.warnings.append(f"Node {node_id} skipped: {reason}")
        
    def record_branch_decision(self, node_id: str, decision: bool) -> None:
        """Record a condition node's branch decision."""
        self.branch_decisions[node_id] = decision
        
    def update_token_usage(self, tokens: int, cost: float = 0.0) -> None:
        """Update token usage tracking."""
        self.total_tokens += tokens
        self.total_cost += cost
        self.api_calls += 1
        
    def should_checkpoint(self) -> bool:
        """Determine if we should create a checkpoint."""
        if not self.checkpoint_enabled:
            return False
            
        # Checkpoint after each level or every 30 seconds
        if self.last_checkpoint is None:
            return True
            
        time_since_checkpoint = (datetime.utcnow() - self.last_checkpoint).total_seconds()
        return time_since_checkpoint > 30
        
    def create_checkpoint(self) -> Dict[str, Any]:
        """Create a checkpoint of current state."""
        self.last_checkpoint = datetime.utcnow()
        return {
            "workflow_id": self.workflow_id,
            "timestamp": self.last_checkpoint.isoformat(),
            "phase": self.phase.value,
            "completed_nodes": list(self.completed_nodes),
            "node_results": {
                node_type.value: {
                    nid: {
                        "success": res.success,
                        "error": res.error,
                        "output": res.output,
                        "execution_time": res.execution_time,
                        "metadata": {
                            "node_id": res.metadata.node_id,
                            "node_type": res.metadata.node_type,
                            "name": res.metadata.name,
                            "version": res.metadata.version,
                            "start_time": res.metadata.start_time.isoformat() if res.metadata.start_time else None,
                            "end_time": res.metadata.end_time.isoformat() if res.metadata.end_time else None,
                            "duration": res.metadata.duration,
                            "error_type": res.metadata.error_type,
                        } if res.metadata else None
                    }
                    for nid, res in results.items()
                }
                for node_type, results in self.node_results.items()
            },
            "branch_decisions": self.branch_decisions.copy(),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }
        
    @classmethod
    def from_checkpoint(cls, checkpoint_data: Dict[str, Any]) -> "WorkflowExecutionState":
        """Restore state from a checkpoint."""
        state = cls(
            workflow_id=checkpoint_data["workflow_id"],
            workflow_name=checkpoint_data.get("workflow_name", "restored"),
        )
        
        # Restore completed nodes
        state.completed_nodes = set(checkpoint_data.get("completed_nodes", []))
        
        # Restore results (would need proper deserialization)
        # state.node_results = checkpoint_data.get("node_results", {})
        
        state.branch_decisions = checkpoint_data.get("branch_decisions", {})
        state.total_tokens = checkpoint_data.get("total_tokens", 0)
        state.total_cost = checkpoint_data.get("total_cost", 0.0)
        
        return state
        
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution state."""
        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "phase": self.phase.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "total_nodes": len(self.completed_nodes) + len(self.failed_nodes) + len(self.skipped_nodes),
            "completed_nodes": len(self.completed_nodes),
            "failed_nodes": len(self.failed_nodes),
            "skipped_nodes": len(self.skipped_nodes),
            "errors": self.errors,
            "warnings": self.warnings,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "api_calls": self.api_calls,
        }
    
    # 🚀 NEW: High-performance analytics methods for nested results
    def get_results_by_node_type(self, node_type: NodeType) -> Dict[str, NodeExecutionResult]:
        """Get all results for a specific node type - perfect for monitoring!"""
        return dict(self.node_results.get(node_type, {}))
    
    def get_node_types_with_results(self) -> List[NodeType]:
        """List all node types that have results - great for dashboard!"""
        return list(self.node_results.keys())
    
    def get_success_rate_by_node_type(self, node_type: NodeType) -> float:
        """Calculate success rate for a specific node type - performance tracking!"""
        results = self.get_results_by_node_type(node_type)
        if not results:
            return 0.0
        successful = sum(1 for result in results.values() if result.success)
        return successful / len(results)
    
    def get_performance_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """🚀 Get comprehensive performance breakdown by node type - ultimate analytics!"""
        breakdown = {}
        for node_type in self.get_node_types_with_results():
            results = self.get_results_by_node_type(node_type)
            total_tokens = sum(
                getattr(result.usage, 'total_tokens', 0) if result.usage else 0 
                for result in results.values()
            )
            total_cost = sum(
                getattr(result.usage, 'total_cost', getattr(result.usage, 'cost', 0.0)) if result.usage else 0.0
                for result in results.values()
            )
            
            breakdown[node_type.value] = {
                "node_count": len(results),
                "success_rate": self.get_success_rate_by_node_type(node_type),
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "avg_tokens_per_node": total_tokens / len(results) if results else 0,
                "avg_cost_per_node": total_cost / len(results) if results else 0.0,
                "nodes": list(results.keys())
            }
        return breakdown 