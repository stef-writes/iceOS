"""Principles for atomic workflow design to prevent over-engineering.

This module enforces constraints to ensure Frosty creates practical,
executable workflows rather than abstract multi-agent fantasies.
"""
from __future__ import annotations

from typing import Any, Dict, List


class AtomicWorkflowPrinciples:
    """Enforces atomic workflow design principles."""
    
    # Node types ranked by complexity (simplest first)
    COMPLEXITY_RANKING = {
        "tool": 1,      # Just call a function
        "llm": 2,       # Single text generation
        "code": 3,      # Custom logic
        "condition": 3, # Simple if/then
        "loop": 4,      # Iteration
        "parallel": 4,  # Concurrent execution
        "human": 5,     # Requires waiting
        "agent": 6,     # Stateful with tools
        "workflow": 7,  # Sub-workflow
        "monitor": 7,   # Long-running watcher
        "recursive": 8, # Complex recursion
        "swarm": 9,     # Multiple agents (AVOID)
    }
    
    # Anti-patterns to detect and prevent
    ANTI_PATTERNS = {
        "swarm_everything": [
            "multiple agents", "collaborate", "consensus", "vote",
            "committee", "team of agents", "swarm"
        ],
        "vague_agents": [
            "AI assistant", "smart agent", "intelligent system",
            "cognitive agent", "reasoning agent"
        ],
        "over_abstraction": [
            "meta-", "self-improving", "adaptive", "evolving",
            "learning system", "neural"
        ],
    }
    
    @staticmethod
    def simplify_node_choice(task_description: str, suggested_type: str) -> str:
        """Simplify node type selection to prefer atomic operations.
        
        Args:
            task_description: What the node needs to do.
            suggested_type: Initially suggested node type.
            
        Returns:
            Simplified node type.
        """
        task_lower = task_description.lower()
        
        # Rule 1: If it's just calling a function, use 'tool'
        if any(word in task_lower for word in ["read", "write", "fetch", "save", "call", "execute"]):
            if "csv" in task_lower or "json" in task_lower or "api" in task_lower:
                return "tool"
        
        # Rule 2: If it's just text generation, use 'llm' not 'agent'
        if suggested_type == "agent" and not any(word in task_lower for word in ["tool", "memory", "state"]):
            return "llm"
        
        # Rule 3: Never default to 'swarm' - require explicit justification
        if suggested_type == "swarm":
            # Only use swarm if explicitly about voting/consensus
            if not any(word in task_lower for word in ["vote", "consensus", "majority"]):
                return "parallel"  # Usually they just want parallel execution
        
        # Rule 4: Prefer 'code' over complex orchestration for calculations
        if any(word in task_lower for word in ["calculate", "transform", "process", "convert"]):
            return "code"
        
        return suggested_type
    
    @staticmethod
    def validate_workflow_practicality(nodes: List[Dict[str, Any]]) -> List[str]:
        """Validate that a workflow is practical and executable.
        
        Args:
            nodes: List of node configurations.
            
        Returns:
            List of warning messages.
        """
        warnings = []
        
        # Check node type distribution
        type_counts: Dict[str, int] = {}
        for node in nodes:
            node_type = node.get("type", "unknown")
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        
        # Warning: Too many agents
        if type_counts.get("agent", 0) > 2:
            warnings.append(
                f"Workflow has {type_counts['agent']} agent nodes. "
                "Consider using 'llm' nodes for stateless operations."
            )
        
        # Warning: Any swarms
        if type_counts.get("swarm", 0) > 0:
            warnings.append(
                "Swarm nodes are complex and rarely needed. "
                "Consider 'parallel' nodes for concurrent execution."
            )
        
        # Warning: No concrete operations
        concrete_types = {"tool", "code", "llm"}
        concrete_count = sum(type_counts.get(t, 0) for t in concrete_types)
        if concrete_count == 0:
            warnings.append(
                "Workflow has no concrete operations (tool/code/llm). "
                "Every workflow needs at least one action node."
            )
        
        # Warning: Too abstract
        total_nodes = len(nodes)
        if total_nodes > 0:
            complexity_score = sum(
                AtomicWorkflowPrinciples.COMPLEXITY_RANKING.get(node.get("type", "unknown"), 10)
                for node in nodes
            ) / total_nodes
            
            if complexity_score > 6:
                warnings.append(
                    "Workflow is too complex. Start with simple tool/llm nodes "
                    "and only add complexity where absolutely necessary."
                )
        
        return warnings
    
    @staticmethod
    def suggest_decomposition(complex_node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Decompose a complex node into simpler atomic operations.
        
        Args:
            complex_node: Node that's too complex.
            
        Returns:
            List of simpler nodes.
        """
        node_type = complex_node.get("type")
        description = complex_node.get("description", "")
        
        if node_type == "swarm":
            # Decompose swarm into parallel LLM calls
            return [
                {
                    "type": "parallel",
                    "description": "Run multiple analyses in parallel",
                    "sub_nodes": [
                        {"type": "llm", "description": "Analysis perspective 1"},
                        {"type": "llm", "description": "Analysis perspective 2"},
                    ]
                },
                {
                    "type": "llm",
                    "description": "Synthesize results from parallel analyses"
                }
            ]
        
        elif node_type == "agent" and "simple" in description.lower():
            # Replace vague agent with specific operation
            return [{
                "type": "llm",
                "description": description.replace("agent", "LLM generation")
            }]
        
        return [complex_node]  # Can't decompose
    
    @staticmethod
    def generate_clarifying_questions(nodes: List[Dict[str, Any]]) -> List[str]:
        """Generate questions to clarify vague node specifications.
        
        Args:
            nodes: Proposed nodes.
            
        Returns:
            List of clarifying questions.
        """
        questions = []
        
        for i, node in enumerate(nodes):
            node_type = node.get("type")
            description = node.get("description", "")
            
            # Question vague agents
            if node_type == "agent" and not node.get("tools"):
                questions.append(
                    f"Step {i+1}: What specific tools does this agent need? "
                    "If none, should this be an 'llm' node instead?"
                )
            
            # Question swarms
            if node_type == "swarm":
                questions.append(
                    f"Step {i+1}: Why does this need multiple agents? "
                    "Would parallel LLM calls achieve the same result?"
                )
            
            # Question abstract descriptions
            if any(word in description.lower() for word in ["process", "handle", "manage"]):
                questions.append(
                    f"Step {i+1}: What specific action happens here? "
                    "(e.g., 'read CSV', 'call API', 'generate summary')"
                )
        
        return questions