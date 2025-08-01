"""Swarm coordination strategies."""
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from ice_core.models.node_models import SwarmNodeConfig


class SwarmStrategy(ABC):
    """Base class for swarm coordination strategies."""
    
    def __init__(self, config: SwarmNodeConfig):
        self.config = config
    
    @abstractmethod
    async def execute(
        self, 
        agents: List[Tuple[Any, Any]], 
        inputs: Dict[str, Any], 
        shared_pool: Any
    ) -> Dict[str, Any]:
        """Execute the coordination strategy."""
        pass

class ConsensusStrategy(SwarmStrategy):
    """Consensus-based coordination where agents iterate until agreement."""
    
    async def execute(
        self, 
        agents: List[Tuple[Any, Any]], 
        inputs: Dict[str, Any], 
        shared_pool: Any
    ) -> Dict[str, Any]:
        """Execute consensus coordination."""
        proposals: List[Dict[str, Any]] = []
        round_num = 0
        
        while round_num < self.config.max_rounds:
            round_results = []
            
            # Execute all agents in parallel for this round
            tasks = []
            for agent, agent_spec in agents:
                agent_context = {
                    **inputs,
                    "round": round_num,
                    "previous_proposals": proposals,
                    "agent_role": agent_spec.role,
                    "shared_context": await shared_pool.get("data", {})
                }
                tasks.append(agent.execute(agent_context))
            
            # Wait for all agents to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and check for consensus
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    continue  # Skip failed agents
                
                agent_spec = agents[i][1]
                round_results.append({
                    "agent_role": agent_spec.role,
                    "proposal": result.get("response", result) if hasattr(result, 'get') else result,
                    "confidence": result.get("confidence", 0.5) if hasattr(result, 'get') else 0.5,
                    "reasoning": result.get("reasoning", "") if hasattr(result, 'get') else ""
                })
            
            # Check for consensus
            if len(round_results) >= 2:
                avg_confidence = sum(r["confidence"] for r in round_results) / len(round_results)
                if avg_confidence >= self.config.consensus_threshold:
                    return {
                        "consensus_reached": True,
                        "final_result": round_results[0]["proposal"],
                        "rounds_completed": round_num + 1,
                        "coordination_strategy": "consensus",
                        "consensus_confidence": avg_confidence,
                        "all_proposals": round_results
                    }
            
            proposals.extend(round_results)
            round_num += 1
        
        # No consensus reached
        best_proposal = max(proposals, key=lambda x: x.get("confidence", 0)) if proposals else {}
        return {
            "consensus_reached": False,
            "final_result": best_proposal,
            "rounds_completed": self.config.max_rounds,
            "coordination_strategy": "consensus",
            "all_proposals": proposals
        }

class HierarchicalStrategy(SwarmStrategy):
    """Hierarchical coordination with specialists → synthesizer → decision."""
    
    async def execute(
        self, 
        agents: List[Tuple[Any, Any]], 
        inputs: Dict[str, Any], 
        shared_pool: Any
    ) -> Dict[str, Any]:
        """Execute hierarchical coordination."""
        # Phase 1: Specialist agents work in parallel
        specialist_results = {}
        specialist_tasks = []
        
        for agent, agent_spec in agents:
            if agent_spec.role not in ["synthesizer", "decision_maker"]:
                task = agent.execute({
                    **inputs,
                    "role_focus": agent_spec.role,
                    "shared_context": await shared_pool.get("data", {})
                })
                specialist_tasks.append((agent_spec.role, task))
        
        # Wait for specialists
        for role, task in specialist_tasks:
            try:
                result = await task
                specialist_results[role] = result
            except Exception as e:
                specialist_results[role] = {"error": str(e)}
        
        # Phase 2: Find synthesizer and combine results
        synthesizer_result = {}
        for agent, agent_spec in agents:
            if agent_spec.role == "synthesizer":
                synthesizer_result = await agent.execute({
                    **inputs,
                    "specialist_inputs": specialist_results,
                    "task": "synthesize_specialist_findings"
                })
                break
        
        return {
            "consensus_reached": True,
            "final_result": synthesizer_result,
            "coordination_strategy": "hierarchical",
            "specialist_findings": specialist_results,
            "rounds_completed": 2
        }

class MarketplaceStrategy(SwarmStrategy):
    """Marketplace-based coordination with bidding mechanisms."""
    
    async def execute(
        self, 
        agents: List[Tuple[Any, Any]], 
        inputs: Dict[str, Any], 
        shared_pool: Any
    ) -> Dict[str, Any]:
        """Execute marketplace coordination."""
        # For now, fallback to consensus - marketplace can be enhanced later
        consensus_strategy = ConsensusStrategy(self.config)
        result = await consensus_strategy.execute(agents, inputs, shared_pool)
        result["coordination_strategy"] = "marketplace"
        return result 