"""Inquiry responder tool for customer service automation."""

from typing import Dict, Any, List
from ice_sdk.tools.base import ToolBase


class InquiryResponderTool(ToolBase):
    """Generates intelligent responses to customer inquiries."""
    
    name: str = "inquiry_responder"
    description: str = "Analyzes customer inquiries and generates appropriate responses"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        # Merge input_data with kwargs for flexibility
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(
        self, 
        inquiry: str,
        customer_history: List[Dict] = None,
        product_context: List[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate intelligent response to customer inquiry."""
        
        if not inquiry:
            return {
                "success": False,
                "error": "No inquiry provided",
                "response": None
            }
        
        customer_history = customer_history or []
        product_context = product_context or []
        
        print(f"🔍 Analyzing inquiry: {inquiry}")
        
        # Analyze inquiry sentiment and intent
        analysis = self._analyze_inquiry(inquiry)
        print(f"📊 Inquiry analysis: {analysis['intent']} (confidence: {analysis['confidence']})")
        
        # Generate appropriate response based on analysis
        response = self._generate_response(
            inquiry=inquiry,
            analysis=analysis,
            customer_history=customer_history,
            product_context=product_context
        )
        
        # Add personalization if customer history available
        if customer_history:
            response = self._personalize_response(response, customer_history)
        
        return {
            "success": True,
            "response": response["message"],
            "confidence": response["confidence"],
            "intent": analysis["intent"],
            "sentiment": analysis["sentiment"],
            "personalized": len(customer_history) > 0,
            "context_used": len(product_context) > 0
        }
    
    def _analyze_inquiry(self, inquiry: str) -> Dict[str, Any]:
        """Analyze customer inquiry for intent and sentiment."""
        
        inquiry_lower = inquiry.lower()
        
        # Intent classification
        intent = "general"
        confidence = 0.6
        
        if any(word in inquiry_lower for word in ["available", "still have", "in stock"]):
            intent = "availability_check"
            confidence = 0.9
        elif any(word in inquiry_lower for word in ["price", "cost", "how much", "deal"]):
            intent = "pricing_inquiry"
            confidence = 0.8
        elif any(word in inquiry_lower for word in ["deliver", "pickup", "shipping", "location"]):
            intent = "delivery_inquiry"
            confidence = 0.8
        elif any(word in inquiry_lower for word in ["condition", "details", "specs", "size"]):
            intent = "product_details"
            confidence = 0.7
        elif any(word in inquiry_lower for word in ["buy", "purchase", "take it", "deal"]):
            intent = "purchase_intent"
            confidence = 0.9
        
        # Sentiment analysis (simplified)
        sentiment = "neutral"
        if any(word in inquiry_lower for word in ["love", "great", "perfect", "excellent"]):
            sentiment = "positive"
        elif any(word in inquiry_lower for word in ["cheap", "expensive", "problem", "issue"]):
            sentiment = "negative"
        
        # Urgency detection
        urgency = "normal"
        if any(word in inquiry_lower for word in ["asap", "urgent", "quickly", "today"]):
            urgency = "high"
        elif any(word in inquiry_lower for word in ["soon", "this week"]):
            urgency = "medium"
        
        return {
            "intent": intent,
            "sentiment": sentiment,
            "urgency": urgency,
            "confidence": confidence
        }
    
    def _generate_response(
        self,
        inquiry: str,
        analysis: Dict[str, Any],
        customer_history: List[Dict],
        product_context: List[Dict]
    ) -> Dict[str, Any]:
        """Generate response based on inquiry analysis."""
        
        intent = analysis["intent"]
        sentiment = analysis["sentiment"]
        urgency = analysis["urgency"]
        
        # Base response templates by intent
        response_templates = {
            "availability_check": {
                "message": "Hi! Yes, this item is still available. Would you like to know more details or arrange pickup/delivery?",
                "confidence": 0.9
            },
            "pricing_inquiry": {
                "message": "Thanks for your interest! The price is as listed, but I'm happy to discuss if you're ready to purchase today.",
                "confidence": 0.8
            },
            "delivery_inquiry": {
                "message": "Great question! We offer both pickup and delivery options. What area are you located in so I can check delivery availability?",
                "confidence": 0.9
            },
            "product_details": {
                "message": "I'd be happy to provide more details! What specific information would be most helpful - condition, dimensions, or features?",
                "confidence": 0.8
            },
            "purchase_intent": {
                "message": "Wonderful! I'm glad you're interested. When would be a good time for pickup or delivery? I can hold this item for you.",
                "confidence": 0.95
            },
            "general": {
                "message": "Thanks for reaching out! I'm here to help with any questions about this item. What would you like to know?",
                "confidence": 0.7
            }
        }
        
        response = response_templates.get(intent, response_templates["general"]).copy()
        
        # Adjust for sentiment
        if sentiment == "positive":
            response["message"] = f"I appreciate your interest! {response['message']}"
            response["confidence"] += 0.05
        elif sentiment == "negative":
            response["message"] = f"I understand your concern. {response['message']}"
            response["confidence"] -= 0.1
        
        # Adjust for urgency
        if urgency == "high":
            response["message"] = response["message"].replace("Would you like", "I can help you right away! Would you like")
            response["confidence"] += 0.05
        
        # Add product context if available
        if product_context:
            context_info = product_context[0]
            if context_info.get("key_features"):
                response["message"] += f" This item features: {context_info['key_features']}."
        
        return response
    
    def _personalize_response(self, response: Dict[str, Any], customer_history: List[Dict]) -> Dict[str, Any]:
        """Personalize response based on customer history."""
        
        # Check for repeat customer
        previous_purchases = [h for h in customer_history if h.get("type") == "purchase"]
        previous_inquiries = [h for h in customer_history if h.get("type") == "inquiry"]
        
        if previous_purchases:
            # Returning customer with purchases
            response["message"] = f"Hi again! Great to hear from you. {response['message']}"
            response["confidence"] += 0.1
        elif len(previous_inquiries) > 2:
            # Customer who asks many questions but hasn't purchased
            response["message"] = f"Thanks for following up! {response['message']}"
            # Slightly encourage action
            if "purchase" not in response["message"].lower():
                response["message"] += " Let me know if you're ready to move forward!"
        
        return response 