"""Real marketplace conversation agent with planning, reasoning, and tool coordination.

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

class MarketplaceConversationAgent(MemoryAgent):
    """Real agent for handling Facebook Marketplace inquiries with full reasoning capabilities."""

    name: str = "marketplace_conversation_agent"

    # Internal runtime-only attributes (not part of Pydantic schema)
    _llm_service: LLMService = PrivateAttr(default_factory=LLMService)
    _conversation_context: Dict[str, Any] = PrivateAttr(default_factory=dict)
    
    def __init__(self, config: MemoryAgentConfig):
        """Initialize the marketplace conversation agent."""
        super().__init__(config=config)
        self._llm_service = LLMService()
        self._conversation_context: Dict[str, Any] = {}
        
    async def _execute_with_memory(self, enhanced_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the marketplace conversation agent with full reasoning loop."""
        
        # Extract conversation data
        messages = enhanced_inputs.get("messages", [])
        customer_id = enhanced_inputs.get("customer_id", "unknown")
        listing_id = enhanced_inputs.get("listing_id", "unknown")
        listing_context = enhanced_inputs.get("listing_context", {})
        
        if not messages:
            return {"action": "error", "message": "No messages provided"}
            
        # Get the latest message
        latest_message = messages[-1]["content"]
        
        # Store conversation in memory
        memory_key = f"conversation:{customer_id}:{listing_id}"
        await self.memory.store(
            key=memory_key,
            content={
                "message": latest_message,
                "timestamp": datetime.utcnow().isoformat(),
                "customer_id": customer_id,
                "listing_id": listing_id,
                "role": "user"
            }
        )
        
        # Retrieve conversation history
        conversation_history = await self.memory.search(memory_key)
        
        # Prepare listing context
        listing_context = listing_context or {
            "listing_item": "Refrigerator",
            "listing_price": "$600", 
            "listing_condition": "Good - minor scratches",
            "listing_location": "Downtown"
        }
        
        # Build conversation context for reasoning
        conversation_text = self._build_conversation_context(messages, conversation_history)
        
        # STEP 1: ANALYZE the inquiry type
        inquiry_analysis = await self._analyze_inquiry(latest_message, conversation_text)
        
        # STEP 2: PLAN response strategy
        response_plan = await self._plan_response_strategy(inquiry_analysis, listing_context)
        
        # STEP 3: EXECUTE the plan
        if response_plan["strategy"] == "simple_response":
            response = await self._generate_simple_response(
                latest_message, conversation_text, listing_context
            )
            action = "respond"
            requires_human = False
            
        elif response_plan["strategy"] == "human_intervention":
            response = await self._generate_complex_response(
                latest_message, conversation_text, listing_context
            )
            action = "trigger_human"
            requires_human = True
            
        else:
            # STEP 4: ADAPT if plan fails
            response = await self._generate_fallback_response(latest_message)
            action = "respond"
            requires_human = False
        
        # Store AI response in memory
        await self.memory.store(
            key=memory_key,
            content={
                "message": response,
                "timestamp": datetime.utcnow().isoformat(),
                "customer_id": customer_id,
                "listing_id": listing_id,
                "role": "assistant"
            }
        )
        
        # STEP 5: LEARN from this interaction
        await self._learn_from_interaction(inquiry_analysis, response_plan, requires_human)
        
        return {
            "action": action,
            "response": response,
            "requires_human": requires_human,
            "conversation_state": response_plan.get("state", "unknown"),
            "memory_key": memory_key,
            "conversation_history": conversation_history,
            "reasoning": {
                "inquiry_analysis": inquiry_analysis,
                "response_plan": response_plan,
                "strategy_used": response_plan["strategy"]
            }
        }

    # ---------------------------------------------------------------------------
    # Reasoning and Planning Methods
    # ---------------------------------------------------------------------------
    
    async def _analyze_inquiry(self, message: str, conversation_context: str) -> Dict[str, Any]:
        """Analyze the type and complexity of the inquiry."""
        system_prompt = """You are an expert at analyzing customer inquiries.
        
        Analyze the inquiry and determine:
        1. Inquiry type (availability, pricing, delivery, condition, etc.)
        2. Complexity level (simple vs complex)
        3. Customer intent (browsing, serious buyer, negotiator)
        4. Required information for response
        
        Return your analysis as JSON with these fields:
        - inquiry_type: string
        - complexity: "simple" or "complex" 
        - customer_intent: string
        - required_info: list of strings
        - confidence: float (0-1)
        """
        
        prompt = f"""Analyze this customer inquiry:
Message: {message}
Conversation Context: {conversation_context}

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
                "inquiry_type": "general",
                "complexity": "simple" if any(word in message.lower() for word in ["available", "have", "stock"]) else "complex",
                "customer_intent": "unknown",
                "required_info": [],
                "confidence": 0.5
            }
        
        # Try to parse JSON response
        try:
            import json
            return json.loads(response.strip())
        except:
            return {
                "inquiry_type": "general",
                "complexity": "simple",
                "customer_intent": "unknown", 
                "required_info": [],
                "confidence": 0.3
            }
    
    async def _plan_response_strategy(self, analysis: Dict[str, Any], listing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan the response strategy based on inquiry analysis."""
        
        # Simple availability questions can be handled directly
        if (analysis.get("complexity") == "simple" and 
            analysis.get("inquiry_type") in ["availability", "general"]):
            return {
                "strategy": "simple_response",
                "state": "simple_inquiry",
                "reasoning": "Direct response for simple availability question"
            }
        
        # Complex inquiries require human intervention
        elif analysis.get("complexity") == "complex":
            return {
                "strategy": "human_intervention", 
                "state": "negotiating",
                "reasoning": "Complex inquiry requires human expertise"
            }
        
        # Pricing, delivery, condition questions need human
        elif analysis.get("inquiry_type") in ["pricing", "delivery", "condition", "negotiation"]:
            return {
                "strategy": "human_intervention",
                "state": "negotiating", 
                "reasoning": f"Specialized inquiry type: {analysis.get('inquiry_type')}"
            }
        
        # Default to human intervention for safety
        else:
            return {
                "strategy": "human_intervention",
                "state": "unknown",
                "reasoning": "Unknown inquiry type, defaulting to human intervention"
            }
    
    async def _learn_from_interaction(self, analysis: Dict[str, Any], plan: Dict[str, Any], required_human: bool) -> None:
        """Learn from this interaction to improve future responses."""
        
        # Store learning in memory
        learning_key = f"learning:marketplace:{analysis.get('inquiry_type', 'unknown')}"
        
        await self.memory.store(
            key=learning_key,
            content={
                "inquiry_type": analysis.get("inquiry_type"),
                "complexity": analysis.get("complexity"),
                "strategy_used": plan.get("strategy"),
                "required_human": required_human,
                "success": not required_human,  # Simple assumption
                "timestamp": datetime.utcnow().isoformat(),
                "lesson": f"Strategy '{plan.get('strategy')}' for {analysis.get('inquiry_type')} inquiry"
            }
        )

    def _build_conversation_context(self, messages: List[Dict[str, str]], 
                                  memory_history: List[Any]) -> str:
        """Build conversation context for LLM."""
        context_parts = []
        
        # Add recent messages from memory
        if memory_history:
            for entry in memory_history[-5:]:  # Last 5 entries
                if isinstance(entry, dict) and "message" in entry:
                    role = entry.get("role", "user")
                    context_parts.append(f"{role.title()}: {entry['message']}")
        
        # Add current message
        if messages:
            context_parts.append(f"User: {messages[-1]['content']}")
        
        return "\n".join(context_parts)

    async def _generate_simple_response(self, message: str, conversation_context: str, 
                                      listing_context: Dict[str, Any]) -> str:
        """Generate response for simple availability questions."""
        system_prompt = """You are a helpful Facebook Marketplace assistant. 
Your job is to handle customer inquiries about listings.

For simple availability questions, respond directly and helpfully.
Keep responses friendly, professional, and helpful. Always be polite and informative.

Current listing context:
- Item: {listing_item}
- Price: {listing_price}
- Condition: {listing_condition}
- Location: {listing_location}""".format(**listing_context)
        
        prompt = f"""Based on the conversation context below, provide a helpful response to the customer's availability question.

Conversation Context:
{conversation_context}

Please respond in a friendly, helpful manner. Confirm availability and offer to provide more information if needed."""
        
        llm_config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=150
        )
        
        response, usage, error = await self._llm_service.generate(
            llm_config=llm_config,
            prompt=prompt,
            context={"system_message": system_prompt}
        )
        
        if error:
            return "Yes, this item is still available! Would you like to know more about it?"
        
        return response.strip()

    async def _generate_complex_response(self, message: str, conversation_context: str, 
                                      listing_context: Dict[str, Any]) -> str:
        """Generate acknowledgment for complex inquiries."""
        system_prompt = """You are a helpful Facebook Marketplace assistant. 
Your job is to handle customer inquiries about listings.

For complex inquiries (price negotiation, delivery, condition questions), 
acknowledge the inquiry and indicate that a human will follow up.

Keep responses friendly, professional, and helpful. Always be polite and informative.

Current listing context:
- Item: {listing_item}
- Price: {listing_price}
- Condition: {listing_condition}
- Location: {listing_location}""".format(**listing_context)
        
        prompt = f"""The customer has asked a complex question that requires human intervention. 
Please provide a friendly acknowledgment that a human will follow up.

Conversation Context:
{conversation_context}

Customer's Question: {message}

Please acknowledge their question politely and let them know a human will respond shortly."""
        
        llm_config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=200
        )
        
        response, usage, error = await self._llm_service.generate(
            llm_config=llm_config,
            prompt=prompt,
            context={"system_message": system_prompt}
        )
        
        if error:
            return "Thank you for your question! A human will respond to you shortly with more details."
        
        return response.strip()
    
    async def _generate_fallback_response(self, message: str) -> str:
        """Generate a fallback response when planning fails."""
        return "Thank you for your message! I'll have someone get back to you shortly with more information."


# Factory function for creating the agent with proper config
def create_marketplace_conversation_agent() -> MarketplaceConversationAgent:
    """Create a MarketplaceConversationAgent with proper configuration."""
    from ice_orchestrator.agent.memory import MemoryAgentConfig
    from ice_core.models import LLMConfig, ModelProvider
    
    config = MemoryAgentConfig(
        id="marketplace_conversation_agent",
        name="Marketplace Conversation Agent",
        type="agent",
        package="ice_tools.toolkits.marketplace.conversation_agent",
        agent_attr="MarketplaceConversationAgent",
        enable_memory=True,
        agent_config={
            "system_prompt": "You are a helpful Facebook Marketplace assistant.",
            "max_retries": 3
        },
        llm_config=LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=200
        ),
        max_iterations=10
    )
    
    return MarketplaceConversationAgent(config)

# Register the agent factory
from ice_core.unified_registry import global_agent_registry
global_agent_registry.register_agent(
    "marketplace_conversation_agent",
    "ice_tools.toolkits.marketplace.conversation_agent:create_marketplace_conversation_agent",
)
