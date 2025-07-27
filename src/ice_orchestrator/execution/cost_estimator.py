"""Workflow cost estimation.

Provides pre-execution cost estimates for better UX.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from ice_core.models import NodeConfig, LLMOperatorConfig, ToolNodeConfig
from ice_orchestrator.providers.costs import TokenCostCalculator


@dataclass
class NodeCostEstimate:
    """Cost estimate for a single node."""
    node_id: str
    node_type: str
    min_cost: float
    max_cost: float
    avg_cost: float
    token_estimate: Optional[int] = None
    api_calls: int = 1
    confidence: float = 0.8  # 0-1 confidence in estimate
    notes: List[str] = None
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []


@dataclass
class WorkflowCostEstimate:
    """Cost estimate for entire workflow."""
    total_min_cost: float
    total_max_cost: float
    total_avg_cost: float
    total_token_estimate: int
    total_api_calls: int
    duration_estimate_seconds: float
    node_estimates: Dict[str, NodeCostEstimate]
    warnings: List[str]
    assumptions: List[str]
    
    def to_user_friendly(self) -> Dict[str, Any]:
        """Convert to user-friendly format for UI display."""
        return {
            "estimated_cost": f"${self.total_avg_cost:.2f} (${self.total_min_cost:.2f} - ${self.total_max_cost:.2f})",
            "estimated_tokens": f"{self.total_token_estimate:,}",
            "estimated_duration": f"{self.duration_estimate_seconds:.1f}s",
            "api_calls": self.total_api_calls,
            "confidence": "high" if all(e.confidence > 0.7 for e in self.node_estimates.values()) else "medium",
            "warnings": self.warnings,
            "breakdown": {
                node_id: {
                    "type": est.node_type,
                    "cost": f"${est.avg_cost:.4f}",
                    "tokens": est.token_estimate,
                    "notes": est.notes
                }
                for node_id, est in self.node_estimates.items()
            }
        }


class WorkflowCostEstimator:
    """Estimates workflow execution costs before running."""
    
    # Default token estimates by node type when we can't calculate exactly
    DEFAULT_TOKEN_ESTIMATES = {
        "llm": {"min": 500, "avg": 1500, "max": 4000},
        "tool": {"min": 0, "avg": 0, "max": 0},
        "agent": {"min": 2000, "avg": 5000, "max": 10000},
        "condition": {"min": 0, "avg": 0, "max": 0},
        "nested_chain": {"min": 1000, "avg": 3000, "max": 8000},
    }
    
    # Execution time estimates (seconds)
    DURATION_ESTIMATES = {
        "llm": {"min": 0.5, "avg": 2.0, "max": 5.0},
        "tool": {"min": 0.1, "avg": 0.5, "max": 2.0},
        "agent": {"min": 5.0, "avg": 15.0, "max": 30.0},
        "condition": {"min": 0.01, "avg": 0.05, "max": 0.1},
        "nested_chain": {"min": 2.0, "avg": 10.0, "max": 30.0},
    }
    
    def __init__(self):
        self.cost_calculator = TokenCostCalculator()
        
    def estimate_workflow_cost(
        self,
        nodes: List[NodeConfig],
        context_size_estimate: int = 1000
    ) -> WorkflowCostEstimate:
        """Estimate cost for entire workflow."""
        node_estimates = {}
        warnings = []
        assumptions = [
            f"Assuming ~{context_size_estimate} tokens of context per node",
            "Costs based on current provider pricing",
            "Actual costs may vary based on dynamic inputs"
        ]
        
        # Estimate each node
        for node in nodes:
            estimate = self._estimate_node_cost(node, context_size_estimate)
            node_estimates[node.id] = estimate
            
            if estimate.confidence < 0.5:
                warnings.append(f"Low confidence estimate for {node.id}")
                
        # Calculate totals
        total_min = sum(e.min_cost for e in node_estimates.values())
        total_max = sum(e.max_cost for e in node_estimates.values())
        total_avg = sum(e.avg_cost for e in node_estimates.values())
        total_tokens = sum(e.token_estimate or 0 for e in node_estimates.values())
        total_calls = sum(e.api_calls for e in node_estimates.values())
        
        # Estimate duration (considering some parallelism)
        duration_by_level = self._estimate_duration_by_level(nodes, node_estimates)
        
        return WorkflowCostEstimate(
            total_min_cost=total_min,
            total_max_cost=total_max,
            total_avg_cost=total_avg,
            total_token_estimate=total_tokens,
            total_api_calls=total_calls,
            duration_estimate_seconds=duration_by_level,
            node_estimates=node_estimates,
            warnings=warnings,
            assumptions=assumptions
        )
        
    def _estimate_node_cost(
        self,
        node: NodeConfig,
        context_size: int
    ) -> NodeCostEstimate:
        """Estimate cost for a single node."""
        node_type = node.type
        
        if isinstance(node, LLMOperatorConfig):
            return self._estimate_llm_cost(node, context_size)
        elif isinstance(node, ToolNodeConfig):
            return self._estimate_tool_cost(node)
        else:
            # Generic estimation
            token_est = self.DEFAULT_TOKEN_ESTIMATES.get(
                node_type, 
                {"min": 100, "avg": 500, "max": 1000}
            )
            
            avg_tokens = token_est["avg"] + context_size
            
            # Assume GPT-3.5 pricing as default
            cost_per_token = 0.002 / 1000  # $0.002 per 1K tokens
            
            return NodeCostEstimate(
                node_id=node.id,
                node_type=node_type,
                min_cost=token_est["min"] * cost_per_token,
                max_cost=token_est["max"] * cost_per_token,
                avg_cost=avg_tokens * cost_per_token,
                token_estimate=avg_tokens,
                confidence=0.5,
                notes=[f"Generic estimate for {node_type} node"]
            )
            
    def _estimate_llm_cost(
        self,
        node: LLMOperatorConfig,
        context_size: int
    ) -> NodeCostEstimate:
        """Estimate cost for LLM node."""
        # Calculate prompt tokens
        prompt_tokens = len(node.prompt.split()) * 1.3  # Rough tokenization
        prompt_tokens += context_size
        
        # Estimate output tokens
        max_tokens = node.max_tokens or 1000
        avg_output_tokens = int(max_tokens * 0.7)  # Assume 70% usage
        
        total_tokens = prompt_tokens + avg_output_tokens
        
        # Get model-specific pricing
        model = node.model
        provider = node.llm_config.provider or "openai"
        
        try:
            cost = self.cost_calculator.calculate_cost(
                model=model,
                input_tokens=prompt_tokens,
                output_tokens=avg_output_tokens,
                provider=provider
            )
            
            return NodeCostEstimate(
                node_id=node.id,
                node_type="llm",
                min_cost=cost * 0.5,  # Might use fewer tokens
                max_cost=cost * 1.5,  # Might use more tokens
                avg_cost=cost,
                token_estimate=total_tokens,
                confidence=0.8,
                notes=[f"Using {model} via {provider}"]
            )
        except Exception:
            # Fallback to generic estimate
            return NodeCostEstimate(
                node_id=node.id,
                node_type="llm",
                min_cost=0.001,
                max_cost=0.01,
                avg_cost=0.005,
                token_estimate=total_tokens,
                confidence=0.3,
                notes=["Could not determine exact model pricing"]
            )
            
    def _estimate_tool_cost(self, node: ToolNodeConfig) -> NodeCostEstimate:
        """Estimate cost for tool node."""
        # Most tools don't have direct costs
        return NodeCostEstimate(
            node_id=node.id,
            node_type="tool",
            min_cost=0.0,
            max_cost=0.0,
            avg_cost=0.0,
            token_estimate=0,
            api_calls=0,
            confidence=1.0,
            notes=[f"Tool: {node.tool_name}"]
        )
        
    def _estimate_duration_by_level(
        self,
        nodes: List[NodeConfig],
        estimates: Dict[str, NodeCostEstimate]
    ) -> float:
        """Estimate total duration considering parallel execution."""
        # Group nodes by level (simplified - would need real DAG)
        total_duration = 0.0
        
        for node in nodes:
            node_type = node.type
            duration = self.DURATION_ESTIMATES.get(
                node_type,
                {"avg": 1.0}
            )["avg"]
            
            # Assume some parallelism reduces total time
            total_duration += duration * 0.7
            
        return total_duration 