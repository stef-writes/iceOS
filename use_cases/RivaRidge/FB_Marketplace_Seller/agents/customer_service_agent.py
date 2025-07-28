"""Customer service agent for Facebook Marketplace interactions."""

from typing import Dict, Any, List
from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig
from ice_sdk.tools.base import ToolBase


class CustomerServiceAgent(MemoryAgent):
    """Handles customer inquiries with memory of past interactions.
    
    This agent:
    - Remembers customer conversation history (episodic memory)
    - Learns from successful interaction patterns (semantic memory)
    - Maintains active conversation state (working memory)
    - Uses tools for external actions (responding, messaging)
    """
    
    async def _execute_with_memory(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle customer inquiry with full context awareness."""
        
        # Extract inquiry information
        inquiry = inputs.get("inquiry", "")
        customer_id = inputs.get("customer_id", "unknown")
        
        print(f"🤖 Customer Service Agent processing inquiry from {customer_id}")
        print(f"💬 Inquiry: {inquiry}")
        
        # Retrieve customer history from episodic memory
        customer_history = []
        if self.memory:
            try:
                history_entries = await self.memory.search(
                    query=f"customer:{customer_id}",
                    memory_types=["episodic"],
                    limit=5
                )
                customer_history = [entry.data for entry in history_entries]
                print(f"📚 Found {len(customer_history)} previous interactions")
            except Exception as e:
                print(f"⚠️  Could not retrieve customer history: {e}")
        
        # Get relevant product knowledge from semantic memory
        product_context = []
        if self.memory:
            try:
                context_entries = await self.memory.search(
                    query=inquiry,
                    memory_types=["semantic"],
                    limit=3,
                    filters={"similarity_threshold": 0.7}
                )
                product_context = [entry.data for entry in context_entries]
                print(f"🧠 Found {len(product_context)} relevant knowledge entries")
            except Exception as e:
                print(f"⚠️  Could not retrieve product context: {e}")
        
        # Analyze inquiry type and determine response strategy
        response_strategy = self._analyze_inquiry_type(inquiry)
        print(f"📋 Inquiry type: {response_strategy['type']}")
        
        # Generate appropriate response
        response_data = await self._generate_response(
            inquiry=inquiry,
            customer_id=customer_id,
            customer_history=customer_history,
            product_context=product_context,
            strategy=response_strategy
        )
        
        # Store this interaction in memory for future reference
        await self._update_memory_with_interaction(
            customer_id=customer_id,
            inquiry=inquiry,
            response=response_data,
            strategy=response_strategy
        )
        
        return {
            "response": response_data["message"],
            "confidence": response_data["confidence"],
            "needs_human": response_data["confidence"] < 0.6,
            "inquiry_type": response_strategy["type"],
            "customer_id": customer_id,
            "interaction_logged": True
        }
    
    def _analyze_inquiry_type(self, inquiry: str) -> Dict[str, Any]:
        """Analyze the type of customer inquiry."""
        
        inquiry_lower = inquiry.lower()
        
        # Availability questions
        if any(word in inquiry_lower for word in ["available", "still have", "in stock"]):
            return {
                "type": "availability",
                "priority": "high",
                "requires_product_check": True
            }
        
        # Delivery/shipping questions  
        elif any(word in inquiry_lower for word in ["deliver", "shipping", "pickup", "location"]):
            return {
                "type": "delivery",
                "priority": "medium", 
                "requires_location_check": True
            }
        
        # Price negotiation
        elif any(word in inquiry_lower for word in ["price", "lowest", "discount", "deal", "negotiate"]):
            return {
                "type": "pricing",
                "priority": "medium",
                "requires_pricing_strategy": True
            }
        
        # Product details
        elif any(word in inquiry_lower for word in ["condition", "details", "specs", "brand", "size"]):
            return {
                "type": "product_details",
                "priority": "low",
                "requires_product_info": True
            }
        
        # General/other
        else:
            return {
                "type": "general",
                "priority": "medium",
                "requires_general_assistance": True
            }
    
    async def _generate_response(
        self,
        inquiry: str,
        customer_id: str,
        customer_history: List[Dict],
        product_context: List[Dict],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate contextual response based on inquiry analysis."""
        
        # Base response templates by inquiry type
        response_templates = {
            "availability": {
                "message": "Hi! Yes, this item is still available. I can check our current inventory for you.",
                "confidence": 0.8
            },
            "delivery": {
                "message": "Great question! We offer both pickup and delivery options. What area are you located in?",
                "confidence": 0.9
            },
            "pricing": {
                "message": "Thanks for your interest! The listed price is competitive, but I'm happy to discuss details. Are you ready to purchase today?",
                "confidence": 0.7
            },
            "product_details": {
                "message": "I'd be happy to provide more details about this item. What specific information are you looking for?",
                "confidence": 0.8
            },
            "general": {
                "message": "Thanks for reaching out! I'm here to help with any questions about our items.",
                "confidence": 0.6
            }
        }
        
        base_response = response_templates.get(strategy["type"], response_templates["general"])
        
        # Personalize based on customer history
        if customer_history:
            # Check if customer is a repeat buyer
            previous_purchases = [h for h in customer_history if h.get("type") == "purchase"]
            if previous_purchases:
                base_response["message"] = f"Hi again! Great to hear from you. {base_response['message']}"
                base_response["confidence"] += 0.1
        
        # Enhance with product context if available
        if product_context and strategy.get("requires_product_info"):
            relevant_info = product_context[0] if product_context else {}
            if relevant_info.get("product_details"):
                base_response["message"] += f" This item is {relevant_info['product_details']}."
                base_response["confidence"] += 0.05
        
        return base_response
    
    async def _update_memory_with_interaction(
        self,
        customer_id: str,
        inquiry: str,
        response: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> None:
        """Store interaction in appropriate memory systems."""
        
        if not self.memory:
            return
        
        interaction_data = {
            "customer_id": customer_id,
            "inquiry": inquiry,
            "response": response["message"],
            "confidence": response["confidence"],
            "inquiry_type": strategy["type"],
            "timestamp": "2025-07-27T13:00:00Z",  # In real implementation, use datetime.now()
            "type": "customer_inquiry"
        }
        
        # Store in episodic memory for customer history
        if self.memory._memories.get("episodic"):
            try:
                await self.memory.store(
                    f"customer:{customer_id}:interaction",
                    interaction_data
                )
                print(f"💾 Stored interaction in episodic memory")
            except Exception as e:
                print(f"⚠️  Failed to store in episodic memory: {e}")
        
        # Store successful patterns in semantic memory
        if response["confidence"] > 0.8 and self.memory._memories.get("semantic"):
            try:
                pattern_data = {
                    "inquiry_pattern": inquiry.lower(),
                    "successful_response": response["message"],
                    "inquiry_type": strategy["type"],
                    "confidence": response["confidence"]
                }
                await self.memory.store(
                    f"pattern:{strategy['type']}",
                    pattern_data
                )
                print(f"🧠 Stored successful pattern in semantic memory")
            except Exception as e:
                print(f"⚠️  Failed to store in semantic memory: {e}")


# Create agent instance for registration
def create_customer_service_agent():
    """Factory function to create configured customer service agent."""
    config = MemoryAgentConfig(
        id="customer_service_agent",
        package="use_cases.RivaRidge.FB_Marketplace_Seller.agents.customer_service_agent",
        tools=[],  # Tools will be injected by orchestrator
        memory_config=None,  # Will use defaults
        enable_memory=True
    )
    return CustomerServiceAgent(config=config) 