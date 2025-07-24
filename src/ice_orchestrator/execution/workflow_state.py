"""Workflow execution state management.

Centralizes all runtime state for cleaner workflow execution logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from enum import Enum

from ice_core.models import NodeExecutionResult


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
    results: Dict[str, NodeExecutionResult] = field(default_factory=dict)
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
    
    # Results and errors
    node_results: Dict[str, NodeExecutionResult] = field(default_factory=dict)
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
        self.node_results[node_id] = result
        
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
                node_id: result.model_dump() 
                for node_id, result in self.node_results.items()
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