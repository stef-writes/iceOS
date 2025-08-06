"""Enhanced marketplace agent with custom memory, tools, and advanced reasoning.

This agent demonstrates:
- Custom memory configuration
- Tool integration and execution
- Advanced reasoning with chain-of-thought
- Multi-step planning and execution
- Learning from interactions
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ice_core.llm.service import LLMService
from ice_core.memory import UnifiedMemory, UnifiedMemoryConfig
from ice_core.models import LLMConfig, ModelProvider
from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig
from pydantic import PrivateAttr


class EnhancedMarketplaceAgent(MemoryAgent):
    """Enhanced marketplace agent with advanced reasoning and tool integration."""

    name: str = "enhanced_marketplace_agent"

    # Internal runtime-only attributes
    _llm_service: LLMService = PrivateAttr(default_factory=LLMService)
    _conversation_context: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _tool_results: Dict[str, Any] = PrivateAttr(default_factory=dict)
    
    def __init__(self, config: MemoryAgentConfig):
        """Initialize the enhanced marketplace agent."""
        super().__init__(config=config)
        self._llm_service = LLMService()
        self._conversation_context = {}
        self._tool_results = {}
        
    async def _execute_with_memory(self, enhanced_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the enhanced agent with advanced reasoning loop."""
        
        # Extract inputs
        messages = enhanced_inputs.get("messages", [])
        customer_id = enhanced_inputs.get("customer_id", "unknown")
        listing_id = enhanced_inputs.get("listing_id", "unknown")
        listing_context = enhanced_inputs.get("listing_context", {})
        
        if not messages:
            return {"action": "error", "message": "No messages provided"}
            
        # Store interaction in memory
        memory_key = f"enhanced_conversation:{customer_id}:{listing_id}"
        await self.memory.store(
            key=memory_key,
            content={
                "messages": messages,
                "timestamp": datetime.utcnow().isoformat(),
                "role": "enhanced_agent"
            }
        )
        
        # Retrieve conversation history and context
        conversation_history = await self.memory.search(memory_key)
        customer_preferences = await self._load_customer_preferences(customer_id)
        product_knowledge = await self._load_product_knowledge(listing_context.get("listing_item", ""))
        
        # STEP 1: ADVANCED ANALYSIS
        analysis = await self._advanced_analysis(
            messages, conversation_history, customer_preferences, product_knowledge
        )
        
        # STEP 2: TOOL PLANNING
        tool_plan = await self._plan_tool_usage(analysis, listing_context)
        
        # STEP 3: TOOL EXECUTION
        tool_results = await self._execute_tools(tool_plan, listing_context)
        
        # STEP 4: ENHANCED REASONING
        reasoning_result = await self._enhanced_reasoning(
            messages, analysis, tool_results, customer_preferences
        )
        
        # STEP 5: RESPONSE GENERATION
        response = await self._generate_enhanced_response(
            reasoning_result, tool_results, customer_preferences
        )
        
        # STEP 6: LEARNING AND MEMORY UPDATE
        await self._learn_from_interaction(analysis, tool_plan, reasoning_result)
        
        return {
            "action": "respond",
            "response": response,
            "reasoning": reasoning_result,
            "tool_results": tool_results,
            "customer_preferences": customer_preferences,
            "memory_key": memory_key
        }
    
    async def _advanced_analysis(
        self, 
        messages: List[Dict[str, str]], 
        history: List[Any],
        preferences: Dict[str, Any],
        knowledge: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Advanced analysis with customer preferences and product knowledge."""
        
        system_prompt = """You are an expert marketplace analyst. Analyze the customer inquiry considering:
        
        1. Customer preferences and history
        2. Product knowledge and features
        3. Conversation context and intent
        4. Potential tool requirements
        
        Return detailed analysis as JSON with:
        - intent: primary customer intent
        - complexity: simple/moderate/complex
        - required_tools: list of tools needed
        - customer_segment: budget/preference segment
        - urgency: low/medium/high
        - confidence: 0-1 score
        """
        
        prompt = f"""Analyze this customer inquiry:

Messages: {messages}
History: {history}
Preferences: {preferences}
Product Knowledge: {knowledge}

Provide detailed analysis:"""
        
        llm_config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.3,
            max_tokens=300
        )
        
        response, usage, error = await self._llm_service.generate(
            llm_config=llm_config,
            prompt=prompt,
            context={"system_message": system_prompt}
        )
        
        if error:
            return {
                "intent": "general_inquiry",
                "complexity": "simple",
                "required_tools": [],
                "customer_segment": "unknown",
                "urgency": "low",
                "confidence": 0.5
            }
        
        try:
            import json
            return json.loads(response.strip())
        except:
            return {
                "intent": "general_inquiry",
                "complexity": "simple", 
                "required_tools": [],
                "customer_segment": "unknown",
                "urgency": "low",
                "confidence": 0.3
            }
    
    async def _plan_tool_usage(self, analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan which tools to use based on analysis."""
        
        required_tools = analysis.get("required_tools", [])
        available_tools = [tool.get("name", "") for tool in self.tools] if self.tools else []
        
        tool_plan = {}
        for tool_name in required_tools:
            if tool_name in available_tools:
                tool_plan[tool_name] = {
                    "needed": True,
                    "parameters": self._get_tool_parameters(tool_name, context)
                }
            else:
                tool_plan[tool_name] = {
                    "needed": True,
                    "available": False,
                    "fallback": "manual_process"
                }
        
        return tool_plan
    
    async def _execute_tools(self, tool_plan: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planned tools and collect results."""
        
        results = {}
        for tool_name, plan in tool_plan.items():
            if plan.get("needed") and plan.get("available", True):
                # Simulate tool execution
                result = await self._simulate_tool_execution(tool_name, plan.get("parameters", {}))
                results[tool_name] = result
            elif plan.get("needed"):
                results[tool_name] = {
                    "status": "unavailable",
                    "fallback": plan.get("fallback", "manual_process")
                }
        
        return results
    
    async def _enhanced_reasoning(
        self,
        messages: List[Dict[str, str]],
        analysis: Dict[str, Any],
        tool_results: Dict[str, Any],
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced reasoning with tool results and preferences."""
        
        system_prompt = """You are an expert marketplace advisor. Use the analysis, tool results, and customer preferences to provide comprehensive reasoning.
        
        Consider:
        - Customer preferences and history
        - Tool results and availability
        - Product knowledge and features
        - Conversation context and intent
        
        Provide reasoning as JSON with:
        - recommendation: primary recommendation
        - reasoning: detailed reasoning
        - alternatives: alternative options
        - next_steps: suggested next steps
        - confidence: 0-1 score
        """
        
        prompt = f"""Provide enhanced reasoning:

Messages: {messages}
Analysis: {analysis}
Tool Results: {tool_results}
Preferences: {preferences}

Provide comprehensive reasoning:"""
        
        llm_config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.4,
            max_tokens=400
        )
        
        response, usage, error = await self._llm_service.generate(
            llm_config=llm_config,
            prompt=prompt,
            context={"system_message": system_prompt}
        )
        
        if error:
            return {
                "recommendation": "contact_human",
                "reasoning": "Unable to process request",
                "alternatives": [],
                "next_steps": ["escalate_to_human"],
                "confidence": 0.3
            }
        
        try:
            import json
            return json.loads(response.strip())
        except:
            return {
                "recommendation": "contact_human",
                "reasoning": "Processing error",
                "alternatives": [],
                "next_steps": ["escalate_to_human"],
                "confidence": 0.2
            }
    
    async def _generate_enhanced_response(
        self,
        reasoning: Dict[str, Any],
        tool_results: Dict[str, Any],
        preferences: Dict[str, Any]
    ) -> str:
        """Generate enhanced response based on reasoning and tool results."""
        
        system_prompt = """You are a helpful marketplace assistant. Generate a personalized response based on:
        
        - Reasoning and recommendations
        - Tool results and availability
        - Customer preferences and style
        - Product knowledge
        
        Be helpful, professional, and personalized to the customer's preferences.
        """
        
        prompt = f"""Generate a personalized response:

Reasoning: {reasoning}
Tool Results: {tool_results}
Preferences: {preferences}

Provide a helpful, personalized response:"""
        
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
            return "Thank you for your inquiry. I'll have someone get back to you shortly with more information."
        
        return response.strip()
    
    async def _load_customer_preferences(self, customer_id: str) -> Dict[str, Any]:
        """Load customer preferences from memory."""
        try:
            preferences = await self.memory.search(f"customer_preferences:{customer_id}")
            return preferences[0] if preferences else {}
        except:
            return {}
    
    async def _load_product_knowledge(self, product_name: str) -> Dict[str, Any]:
        """Load product knowledge from memory."""
        try:
            knowledge = await self.memory.search(f"product_knowledge:{product_name.lower()}")
            return knowledge[0] if knowledge else {}
        except:
            return {}
    
    def _get_tool_parameters(self, tool_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get parameters for tool execution."""
        if tool_name == "price_calculator":
            return {
                "base_price": float(context.get("listing_price", "0").replace("$", "")),
                "discount_percent": 0.0
            }
        elif tool_name == "delivery_scheduler":
            return {
                "zip_code": "12345",  # Would come from context
                "preferred_date": "2024-01-15"
            }
        elif tool_name == "inventory_checker":
            return {
                "product_id": context.get("product_id", "unknown")
            }
        return {}
    
    async def _simulate_tool_execution(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate tool execution."""
        if tool_name == "price_calculator":
            base_price = parameters.get("base_price", 0)
            discount = parameters.get("discount_percent", 0)
            final_price = base_price * (1 - discount / 100)
            return {
                "status": "success",
                "final_price": round(final_price, 2),
                "discount_applied": discount
            }
        elif tool_name == "delivery_scheduler":
            return {
                "status": "success",
                "available_dates": ["2024-01-15", "2024-01-16", "2024-01-17"],
                "delivery_fee": 50.0
            }
        elif tool_name == "inventory_checker":
            return {
                "status": "success",
                "in_stock": True,
                "quantity": 3
            }
        return {"status": "unknown_tool"}
    
    async def _learn_from_interaction(
        self, 
        analysis: Dict[str, Any], 
        tool_plan: Dict[str, Any], 
        reasoning: Dict[str, Any]
    ) -> None:
        """Learn from this interaction to improve future responses."""
        
        learning_key = f"learning:enhanced_agent:{analysis.get('intent', 'unknown')}"
        
        await self.memory.store(
            key=learning_key,
            content={
                "intent": analysis.get("intent"),
                "complexity": analysis.get("complexity"),
                "tools_used": list(tool_plan.keys()),
                "reasoning_confidence": reasoning.get("confidence"),
                "timestamp": datetime.utcnow().isoformat(),
                "lesson": f"Enhanced reasoning for {analysis.get('intent')} intent"
            }
        )


# Factory function for creating the enhanced agent
def create_enhanced_marketplace_agent() -> EnhancedMarketplaceAgent:
    """Create an EnhancedMarketplaceAgent with proper configuration."""
    from ice_orchestrator.agent.memory import MemoryAgentConfig
    from ice_core.models import LLMConfig, ModelProvider
    
    config = MemoryAgentConfig(
        id="enhanced_marketplace_agent",
        name="Enhanced Marketplace Agent",
        type="agent",
        package="ice_tools.toolkits.marketplace.enhanced_agent",
        agent_attr="EnhancedMarketplaceAgent",
        enable_memory=True,
        agent_config={
            "system_prompt": "You are an enhanced marketplace assistant with advanced reasoning capabilities.",
            "max_retries": 3
        },
        llm_config=LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=300
        ),
        max_iterations=15
    )
    
    return EnhancedMarketplaceAgent(config)

# Register the enhanced agent factory
from ice_core.unified_registry import global_agent_registry
global_agent_registry.register_agent(
    "enhanced_marketplace_agent",
    "ice_tools.toolkits.marketplace.enhanced_agent:create_enhanced_marketplace_agent",
) 