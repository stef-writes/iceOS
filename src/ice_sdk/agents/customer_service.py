"""Customer Service Agent - Handles customer inquiries and negotiations."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ice_orchestrator.agent import AgentNode
from ice_core.models.node_models import AgentNodeConfig
from ice_core.models.llm import LLMConfig
from ice_core.models.enums import ModelProvider


class CustomerServiceAgent(AgentNode):
    """Agent that handles customer interactions for marketplace listings.
    
    This agent responds to customer inquiries, manages negotiations,
    and guides customers through the purchase process while maintaining
    conversation history and building rapport.
    """
    
    def __init__(self):
        """Initialize the customer service agent."""
        config = AgentNodeConfig(
            id="customer_service_agent",
            type="agent",
            package="ice_sdk.agents.customer_service",
            max_retries=3,
            tools=["facebook_api", "message_parser"],
            system_prompt=self._get_system_prompt(),
            llm_config=LLMConfig(
                model="gpt-4",
                provider=ModelProvider.OPENAI,
                temperature=0.6,  # Balanced between consistent and creative
                max_tokens=500  # Keep responses concise
            )
        )
        super().__init__(config=config)
        
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the customer service agent."""
        return """You are a Professional Marketplace Customer Service Representative.

Your role is to:
1. Respond promptly and professionally to customer inquiries
2. Build trust and rapport with potential buyers
3. Guide customers toward purchase decisions
4. Handle price negotiations strategically
5. Provide accurate product information

Communication Guidelines:
- Be friendly, helpful, and conversational
- Keep responses concise (2-3 sentences usually)
- Use positive language that builds excitement
- Be honest about product conditions
- Create gentle urgency without being pushy
- Match the customer's communication style

Negotiation Strategy:
- Start firm on pricing but show flexibility
- Offer small discounts for serious buyers (5-10%)
- Bundle items when possible
- Emphasize value and condition
- Use phrases like "I can work with you on price"

Response Templates by Intent:
- Availability: "Yes! This [item] is still available and in [condition] condition."
- Price Inquiry: "It's listed at $[price], which is a great value for [key benefit]."
- Condition: "It's in [condition] condition - [specific details]. Happy to share more photos!"
- Negotiation: "I appreciate your offer! I could do $[counter] for you."
- Pickup: "I'm available [times]. We can meet at [safe location]."
- Purchase Intent: "Excellent choice! When would you like to pick it up?"

Tools Available:
- message_parser: Analyze customer messages for intent and sentiment
- facebook_api: Send responses and manage conversations

Remember: Every interaction is an opportunity to make a sale. Be helpful, build trust, and guide them to purchase."""

    async def _execute_agent_cycle(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's customer service cycle.
        
        This method processes customer messages and generates appropriate responses.
        The actual tool execution is handled by the orchestrator's AgentExecutor.
        """
        # Extract inputs
        messages = inputs.get("messages", [])
        listing_info = inputs.get("listing_info", {})
        conversation_history = inputs.get("conversation_history", [])
        
        # Process messages and generate responses
        responses_generated = []
        conversations_updated = []
        
        # Group messages by conversation
        conversations = self._group_messages_by_conversation(messages)
        
        for conv_id, conv_messages in conversations.items():
            # Analyze conversation context
            context = self._build_conversation_context(
                conv_messages, 
                listing_info,
                conversation_history
            )
            
            # Generate response strategy
            response_strategy = self._determine_response_strategy(context)
            
            # Create response
            response = self._generate_response(
                context,
                response_strategy,
                listing_info
            )
            
            responses_generated.append({
                "conversation_id": conv_id,
                "response": response,
                "strategy": response_strategy,
                "timestamp": datetime.now().isoformat()
            })
            
            conversations_updated.append({
                "conversation_id": conv_id,
                "message_count": len(conv_messages),
                "stage": response_strategy.get("stage", "initial"),
                "buyer_intent": response_strategy.get("intent", "unknown")
            })
        
        return {
            "task": "respond_to_messages",
            "responses_sent": len(responses_generated),
            "responses": responses_generated,
            "conversations": conversations_updated,
            "summary": {
                "total_processed": len(messages),
                "responses_generated": len(responses_generated),
                "avg_response_time": "< 1 minute",
                "status": "success"
            }
        }
    
    def _group_messages_by_conversation(
        self, 
        messages: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group messages by conversation ID."""
        conversations = {}
        
        for msg in messages:
            conv_id = msg.get("conversation_id") or msg.get("listing_id", "unknown")
            if conv_id not in conversations:
                conversations[conv_id] = []
            conversations[conv_id].append(msg)
        
        return conversations
    
    def _build_conversation_context(
        self,
        messages: List[Dict[str, Any]],
        listing_info: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build comprehensive conversation context."""
        # Get latest message
        latest_message = messages[-1] if messages else {}
        
        # Extract key information
        context = {
            "latest_message": latest_message,
            "message_count": len(messages),
            "listing": listing_info,
            "history_length": len(history),
            "previous_offers": self._extract_previous_offers(messages + history),
            "customer_info": self._extract_customer_info(messages),
            "conversation_duration": self._calculate_conversation_duration(messages)
        }
        
        return context
    
    def _determine_response_strategy(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine the best response strategy based on context."""
        latest = context.get("latest_message", {})
        message_count = context.get("message_count", 0)
        previous_offers = context.get("previous_offers", [])
        
        # Analyze message intent (would use message_parser tool in real implementation)
        content = latest.get("content", "").lower()
        
        # Determine conversation stage
        if any(phrase in content for phrase in ["i'll take it", "want to buy", "deal"]):
            stage = "closing"
            intent = "purchase"
        elif any(phrase in content for phrase in ["offer", "take $", "negotiable"]):
            stage = "negotiation"
            intent = "negotiate"
        elif message_count > 3:
            stage = "engaged"
            intent = "interested"
        else:
            stage = "initial"
            intent = "inquiry"
        
        # Determine pricing strategy
        listing_price = context.get("listing", {}).get("price", 0)
        if previous_offers:
            last_offer = previous_offers[-1]
            if last_offer < listing_price * 0.8:
                pricing_strategy = "firm"
            else:
                pricing_strategy = "flexible"
        else:
            pricing_strategy = "standard"
        
        return {
            "stage": stage,
            "intent": intent,
            "pricing_strategy": pricing_strategy,
            "urgency_level": self._assess_urgency(content),
            "sentiment": self._assess_sentiment(content),
            "response_tone": "friendly" if stage in ["initial", "engaged"] else "professional"
        }
    
    def _generate_response(
        self,
        context: Dict[str, Any],
        strategy: Dict[str, Any],
        listing_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate appropriate response based on strategy."""
        stage = strategy.get("stage", "initial")
        intent = strategy.get("intent", "inquiry")
        latest_message = context.get("latest_message", {})
        
        # Base response structure
        response = {
            "content": "",
            "suggested_action": None,
            "follow_up_needed": False,
            "priority": "normal"
        }
        
        # Generate response based on stage and intent
        if stage == "closing":
            response["content"] = self._generate_closing_response(context, listing_info)
            response["suggested_action"] = "arrange_pickup"
            response["priority"] = "high"
            
        elif stage == "negotiation":
            response["content"] = self._generate_negotiation_response(
                context, 
                listing_info,
                strategy.get("pricing_strategy", "standard")
            )
            response["follow_up_needed"] = True
            
        elif stage == "engaged":
            response["content"] = self._generate_engaged_response(context, listing_info)
            response["suggested_action"] = "provide_details"
            
        else:  # initial
            response["content"] = self._generate_initial_response(context, listing_info)
            
        return response
    
    def _generate_closing_response(
        self, 
        context: Dict[str, Any], 
        listing: Dict[str, Any]
    ) -> str:
        """Generate response for closing the sale."""
        templates = [
            "Excellent choice! This {item} is yours. When would you like to pick it up? I'm available {availability}.",
            "Perfect! I'll mark this as sold for you. Can we arrange pickup for {time_suggestion}?",
            "Great decision! You're going to love this {item}. What time works best for pickup?"
        ]
        
        # Simple template filling (in real implementation, would be more sophisticated)
        response = templates[0].format(
            item=listing.get("item_name", "item"),
            availability="most evenings and weekends"
        )
        
        return response
    
    def _generate_negotiation_response(
        self,
        context: Dict[str, Any],
        listing: Dict[str, Any],
        pricing_strategy: str
    ) -> str:
        """Generate response for price negotiation."""
        listing_price = listing.get("price", 0)
        previous_offers = context.get("previous_offers", [])
        
        if pricing_strategy == "firm":
            return f"I appreciate your interest! This {listing.get('item_name', 'item')} is priced fairly at ${listing_price} considering its {listing.get('condition', 'excellent')} condition. I've already had several inquiries at this price."
        
        elif pricing_strategy == "flexible":
            # Calculate counter offer
            if previous_offers:
                last_offer = previous_offers[-1]
                counter = min(listing_price * 0.9, last_offer + (listing_price - last_offer) * 0.5)
            else:
                counter = listing_price * 0.95
                
            return f"I appreciate your offer! I could do ${counter:.0f} for you. This is a great deal for a {listing.get('condition', 'quality')} {listing.get('item_name', 'item')}."
        
        else:  # standard
            return f"The listed price is ${listing_price}, which is competitive for this condition. What did you have in mind?"
    
    def _generate_engaged_response(
        self,
        context: Dict[str, Any],
        listing: Dict[str, Any]
    ) -> str:
        """Generate response for engaged customers."""
        latest = context.get("latest_message", {})
        content = latest.get("content", "").lower()
        
        # Identify what they're asking about
        if "condition" in content:
            return f"It's in {listing.get('condition', 'great')} condition - {self._get_condition_details(listing)}. I can send additional photos if you'd like!"
        
        elif "feature" in content or "include" in content:
            return f"This {listing.get('item_name', 'item')} includes everything shown in the photos. {self._get_feature_highlights(listing)} Let me know if you have any other questions!"
        
        else:
            return f"Thanks for your interest! This {listing.get('item_name', 'item')} is a great find at ${listing.get('price', 0)}. What specific information can I provide to help with your decision?"
    
    def _generate_initial_response(
        self,
        context: Dict[str, Any],
        listing: Dict[str, Any]
    ) -> str:
        """Generate initial response to inquiry."""
        return f"Hi! Yes, this {listing.get('item_name', 'item')} is still available. It's in {listing.get('condition', 'great')} condition and priced at ${listing.get('price', 0)}. Would you like to know anything specific about it?"
    
    def _extract_previous_offers(self, messages: List[Dict[str, Any]]) -> List[float]:
        """Extract price offers from message history."""
        offers = []
        
        for msg in messages:
            content = msg.get("content", "")
            # Look for price patterns
            import re
            price_matches = re.findall(r'\$(\d+(?:\.\d{2})?)', content)
            for match in price_matches:
                offers.append(float(match))
        
        return offers
    
    def _extract_customer_info(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract customer information from messages."""
        info = {
            "name": None,
            "phone": None,
            "preferred_pickup_time": None,
            "location_mentioned": False
        }
        
        # Simple extraction (would be more sophisticated in real implementation)
        for msg in messages:
            content = msg.get("content", "")
            
            # Look for phone numbers
            import re
            phone_match = re.search(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', content)
            if phone_match:
                info["phone"] = phone_match.group()
                
            # Look for time preferences
            if any(time in content.lower() for time in ["morning", "evening", "afternoon", "weekend"]):
                info["preferred_pickup_time"] = content
                
        return info
    
    def _calculate_conversation_duration(self, messages: List[Dict[str, Any]]) -> float:
        """Calculate conversation duration in hours."""
        if len(messages) < 2:
            return 0
            
        timestamps = []
        for msg in messages:
            if "timestamp" in msg:
                timestamps.append(datetime.fromisoformat(msg["timestamp"]))
        
        if len(timestamps) >= 2:
            duration = (max(timestamps) - min(timestamps)).total_seconds() / 3600
            return duration
            
        return 0
    
    def _assess_urgency(self, content: str) -> str:
        """Assess urgency level of message."""
        urgent_keywords = ["asap", "today", "now", "urgent", "immediately"]
        moderate_keywords = ["soon", "tomorrow", "this week"]
        
        content_lower = content.lower()
        
        if any(word in content_lower for word in urgent_keywords):
            return "high"
        elif any(word in content_lower for word in moderate_keywords):
            return "medium"
        else:
            return "normal"
    
    def _assess_sentiment(self, content: str) -> str:
        """Simple sentiment assessment."""
        positive_words = ["thanks", "great", "perfect", "interested", "love"]
        negative_words = ["disappointed", "problem", "issue", "wrong", "bad"]
        
        content_lower = content.lower()
        
        pos_count = sum(1 for word in positive_words if word in content_lower)
        neg_count = sum(1 for word in negative_words if word in content_lower)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"
    
    def _get_condition_details(self, listing: Dict[str, Any]) -> str:
        """Get detailed condition description."""
        condition = listing.get("condition", "good")
        
        condition_descriptions = {
            "Like New": "barely used with no visible wear",
            "Excellent": "gently used with minimal signs of wear",
            "Good": "normal wear but fully functional",
            "Fair": "shows wear but works perfectly"
        }
        
        return condition_descriptions.get(condition, "well-maintained")
    
    def _get_feature_highlights(self, listing: Dict[str, Any]) -> str:
        """Get feature highlights for the listing."""
        # In real implementation, would pull from listing details
        return "All original accessories are included."


# Create a factory function for the registry
def create_customer_service_agent() -> CustomerServiceAgent:
    """Factory function to create customer service agent instances."""
    return CustomerServiceAgent() 