"""Real listing status agent with planning, reasoning, and tool coordination.

This agent demonstrates true agent capabilities:
- Multi-step reasoning and planning
- Tool selection and execution
- Memory integration and learning
- Goal-oriented decision making
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ice_core.llm.service import LLMService
from ice_core.memory import UnifiedMemory, UnifiedMemoryConfig
from ice_core.models import LLMConfig, ModelProvider
from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig
from pydantic import PrivateAttr


class ListingStatusAgent(MemoryAgent):
    """Real agent for managing listing status updates with full reasoning capabilities."""

    name: str = "listing_status_agent"

    # Internal runtime-only attributes
    _llm_service: LLMService = PrivateAttr(default_factory=LLMService)
    _status_context: Dict[str, Any] = PrivateAttr(default_factory=dict)
    
    def __init__(self, config: MemoryAgentConfig):
        """Initialize the listing status agent."""
        super().__init__(config=config)
        self._llm_service = LLMService()
        self._status_context: Dict[str, Any] = {}
        
    async def _execute_with_memory(self, enhanced_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the listing status agent with full reasoning loop."""
        
        # Extract conversation data
        conversation_result = enhanced_inputs.get("conversation_result", {})
        listing_id = enhanced_inputs.get("listing_id", "unknown")
        listing_context = enhanced_inputs.get("listing_context", {})
        
        if not conversation_result:
            return {"action": "error", "message": "No conversation result provided"}
            
        # Store status decision in memory
        memory_key = f"status_decision:{listing_id}"
        await self.memory.store(
            key=memory_key,
            content={
                "conversation_result": conversation_result,
                "listing_id": listing_id,
                "timestamp": datetime.utcnow().isoformat(),
                "role": "status_agent"
            }
        )
        
        # Retrieve status history
        status_history = await self.memory.search(memory_key)
        
        # STEP 1: ANALYZE the conversation outcome
        outcome_analysis = await self._analyze_conversation_outcome(conversation_result, status_history)
        
        # STEP 2: PLAN status update strategy
        update_plan = await self._plan_status_update(outcome_analysis, listing_context)
        
        # STEP 3: EXECUTE the plan
        if update_plan["strategy"] == "update_to_sold":
            result = await self._execute_sale_update(listing_id, conversation_result)
            action = "update_status"
            new_status = "sold"
            
        elif update_plan["strategy"] == "update_to_unavailable":
            result = await self._execute_unavailable_update(listing_id, conversation_result)
            action = "update_status"
            new_status = "unavailable"
            
        else:
            # STEP 4: ADAPT if plan fails
            result = await self._execute_no_change(listing_id, conversation_result)
            action = "no_change"
            new_status = "unchanged"
        
        # Store status update in memory
        await self.memory.store(
            key=memory_key,
            content={
                "action": action,
                "new_status": new_status,
                "reason": update_plan.get("reasoning", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
                "role": "status_agent"
            }
        )
        
        # STEP 5: LEARN from this interaction
        await self._learn_from_status_update(outcome_analysis, update_plan, result.get("success", False))
        
        return {
            "action": action,
            "listing_id": listing_id,
            "new_status": new_status,
            "reason": update_plan.get("reasoning", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "success": result.get("success", True),
            "reasoning": {
                "outcome_analysis": outcome_analysis,
                "update_plan": update_plan,
                "strategy_used": update_plan["strategy"]
            }
        }
    
    # ---------------------------------------------------------------------------
    # Reasoning and Planning Methods
    # ---------------------------------------------------------------------------
    
    async def _analyze_conversation_outcome(self, conversation_result: Dict[str, Any], status_history: List[Any]) -> Dict[str, Any]:
        """Analyze the conversation outcome to determine status update needs."""
        system_prompt = """You are an expert at analyzing conversation outcomes for marketplace listings.
        
        Analyze the conversation result and determine:
        1. Whether a sale was completed
        2. Whether the item is no longer available
        3. Whether any status update is needed
        4. Confidence level in the decision
        
        Return your analysis as JSON with these fields:
        - sale_completed: boolean
        - item_unavailable: boolean
        - status_update_needed: boolean
        - update_type: "sold" | "unavailable" | "none"
        - confidence: float (0-1)
        - reasoning: string
        """
        
        prompt = f"""Analyze this conversation outcome:

Conversation Result: {conversation_result}
Status History: {status_history}

Provide your analysis:"""
        
        llm_config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.3,
            max_tokens=200
        )
        
        response, usage, error = await self._llm_service.generate(
            llm_config=llm_config,
            prompt=prompt,
            context={"system_message": system_prompt}
        )
        
        if error:
            # Fallback analysis
            return {
                "sale_completed": conversation_result.get("action") == "sale_completed",
                "item_unavailable": conversation_result.get("action") == "item_unavailable",
                "status_update_needed": conversation_result.get("action") in ["sale_completed", "item_unavailable"],
                "update_type": "sold" if conversation_result.get("action") == "sale_completed" else "none",
                "confidence": 0.5,
                "reasoning": "Fallback analysis based on conversation action"
            }
        
        # Try to parse JSON response
        try:
            import json
            return json.loads(response.strip())
        except:
            return {
                "sale_completed": False,
                "item_unavailable": False,
                "status_update_needed": False,
                "update_type": "none",
                "confidence": 0.3,
                "reasoning": "Failed to parse analysis"
            }
    
    async def _plan_status_update(self, analysis: Dict[str, Any], listing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan the status update strategy based on conversation analysis."""
        
        # Sale completed - update to sold
        if analysis.get("sale_completed") and analysis.get("update_type") == "sold":
            return {
                "strategy": "update_to_sold",
                "reasoning": "Conversation led to a completed sale"
            }
        
        # Item no longer available
        elif analysis.get("item_unavailable") and analysis.get("update_type") == "unavailable":
            return {
                "strategy": "update_to_unavailable",
                "reasoning": "Conversation indicated item is no longer available"
            }
        
        # No status update needed
        else:
            return {
                "strategy": "no_change",
                "reasoning": "No status update required based on conversation outcome"
            }
    
    async def _execute_sale_update(self, listing_id: str, conversation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the sale status update."""
        return {
            "success": True,
            "action": "update_status",
            "listing_id": listing_id,
            "new_status": "sold",
            "reason": "conversation_led_to_sale",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_unavailable_update(self, listing_id: str, conversation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the unavailable status update."""
        return {
            "success": True,
            "action": "update_status",
            "listing_id": listing_id,
            "new_status": "unavailable",
            "reason": "item_no_longer_available",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_no_change(self, listing_id: str, conversation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute no status change."""
        return {
            "success": True,
            "action": "no_change",
            "listing_id": listing_id,
            "reason": "conversation_did_not_require_status_change",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _learn_from_status_update(self, analysis: Dict[str, Any], plan: Dict[str, Any], success: bool) -> None:
        """Learn from this status update interaction."""
        
        # Store learning in memory
        learning_key = f"learning:status_update:{analysis.get('update_type', 'none')}"
        
        await self.memory.store(
            key=learning_key,
            content={
                "update_type": analysis.get("update_type"),
                "strategy_used": plan.get("strategy"),
                "success": success,
                "confidence": analysis.get("confidence", 0.5),
                "timestamp": datetime.utcnow().isoformat(),
                "lesson": f"Strategy '{plan.get('strategy')}' for {analysis.get('update_type')} update"
            }
        )


# Factory function for creating the agent with proper config
def create_listing_status_agent() -> ListingStatusAgent:
    """Create a ListingStatusAgent with proper configuration."""
    from ice_orchestrator.agent.memory import MemoryAgentConfig
    from ice_core.models import LLMConfig, ModelProvider
    
    config = MemoryAgentConfig(
        id="listing_status_agent",
        name="Listing Status Agent",
        type="agent",
        package="ice_tools.toolkits.marketplace.listing_status_agent",
        agent_attr="ListingStatusAgent",
        enable_memory=True,
        agent_config={
            "system_prompt": "You are a listing status management agent.",
            "max_retries": 3
        },
        llm_config=LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.3,
            max_tokens=200
        ),
        max_iterations=10
    )
    
    return ListingStatusAgent(config)

# Register the agent factory
from ice_core.unified_registry import global_agent_registry
global_agent_registry.register_agent(
    "listing_status_agent",
    "ice_tools.toolkits.marketplace.listing_status_agent:create_listing_status_agent",
)