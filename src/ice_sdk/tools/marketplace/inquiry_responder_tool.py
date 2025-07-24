"""Inquiry Responder Tool for handling marketplace buyer questions.

Generates appropriate responses to common buyer inquiries while
maintaining a professional and helpful tone.
"""

from typing import Any, Dict, List, Optional
from pydantic import Field

from ice_core.base_tool import ToolBase


class InquiryResponderTool(ToolBase):
    """Generates responses to marketplace buyer inquiries."""
    
    name: str = "inquiry_responder"
    description: str = "Creates appropriate responses to buyer questions"
    
    # Common inquiry patterns and template responses
    RESPONSE_TEMPLATES = {
        "availability": {
            "keywords": ["available", "still have", "sold", "in stock"],
            "response": "Hi! Yes, this {product} is still available. We have {stock} units in stock. Would you like to arrange a viewing or pickup?"
        },
        "price_negotiation": {
            "keywords": ["lower", "negotiate", "best price", "discount", "offer"],
            "response": "Hi! The listed price of ${price} is already {discount}% below retail. For bulk purchases (5+ units), I can offer an additional 5% off. What quantity are you interested in?"
        },
        "condition_questions": {
            "keywords": ["condition", "working", "damaged", "tested", "warranty"],
            "response": "Hi! This item is in {condition} condition. {condition_details} All items are tested before listing. While we don't offer warranty on surplus items, you're welcome to inspect before purchase."
        },
        "pickup_delivery": {
            "keywords": ["pickup", "deliver", "ship", "location", "meet"],
            "response": "Hi! Pickup is available at {location}. For bulk orders, we can arrange delivery within 10 miles for a small fee. When would you like to pick up?"
        },
        "bulk_inquiry": {
            "keywords": ["bulk", "wholesale", "multiple", "all", "quantity"],
            "response": "Hi! Great question about bulk purchasing. We have {stock} units available. For orders of 10+ units, we offer 10% off. For 50+ units, 15% off. How many were you thinking?"
        },
        "payment_methods": {
            "keywords": ["payment", "cash", "venmo", "paypal", "pay"],
            "response": "Hi! We accept cash, Venmo, PayPal, and Zelle. Cash preferred for in-person pickups. Which works best for you?"
        },
        "item_details": {
            "keywords": ["specs", "details", "more info", "specifications", "size"],
            "response": "Hi! Here are the details for this {product}:\n{product_details}\nIs there anything specific you'd like to know?"
        }
    }
    
    # Condition-specific details
    CONDITION_DETAILS = {
        "New": "It's brand new in original packaging, never opened or used.",
        "Open Box": "The box was opened for inspection but the item was never used. All original accessories included.",
        "Refurbished": "Professionally refurbished to work like new. Fully tested and cleaned.",
        "Used": "Previously used but in good working condition. Shows normal signs of wear."
    }
    
    async def _execute_impl(
        self,
        inquiry: str = Field(..., description="The buyer's inquiry message"),
        product: Dict[str, Any] = Field(..., description="Product details"),
        generate_alternatives: bool = Field(True, description="Generate alternative responses"),
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generate response to buyer inquiry."""
        
        # Analyze inquiry type
        inquiry_type = self._classify_inquiry(inquiry.lower())
        
        # Generate primary response
        primary_response = self._generate_response(inquiry_type, product, inquiry)
        
        # Generate alternatives if requested
        alternatives = []
        if generate_alternatives:
            alternatives = self._generate_alternatives(inquiry_type, product)
        
        # Generate follow-up suggestions
        follow_ups = self._suggest_follow_ups(inquiry_type, product)
        
        return {
            "inquiry_type": inquiry_type,
            "primary_response": primary_response,
            "alternative_responses": alternatives,
            "suggested_follow_ups": follow_ups,
            "response_time": "Respond within 1 hour for best results",
            "tone": "Friendly, professional, helpful"
        }
    
    def _classify_inquiry(self, inquiry: str) -> str:
        """Classify the type of inquiry based on keywords."""
        for inquiry_type, template in self.RESPONSE_TEMPLATES.items():
            if any(keyword in inquiry for keyword in template["keywords"]):
                return inquiry_type
        return "general"
    
    def _generate_response(
        self, 
        inquiry_type: str, 
        product: Dict[str, Any],
        original_inquiry: str
    ) -> str:
        """Generate appropriate response based on inquiry type."""
        
        if inquiry_type == "general":
            # Generic response for unclassified inquiries
            return (
                f"Hi! Thanks for your interest in the {product['product_name']}. "
                f"It's currently available for ${product.get('suggested_price', product['price'])}. "
                "How can I help you today?"
            )
        
        template = self.RESPONSE_TEMPLATES[inquiry_type]["response"]
        
        # Fill in template variables
        response = template.format(
            product=product['product_name'],
            stock=product.get('current_stock', 'multiple'),
            price=product.get('suggested_price', product.get('price', 'N/A')),
            discount=product.get('discount_percentage', 20),
            condition=product.get('condition', 'good'),
            condition_details=self.CONDITION_DETAILS.get(
                product.get('condition', 'Used'), 
                "Item is in the stated condition."
            ),
            location=product.get('location', 'our warehouse'),
            product_details=self._format_product_details(product)
        )
        
        return response
    
    def _generate_alternatives(
        self, 
        inquiry_type: str, 
        product: Dict[str, Any]
    ) -> List[str]:
        """Generate alternative response options."""
        alternatives = []
        
        if inquiry_type == "price_negotiation":
            alternatives.append(
                f"Hi! I understand you're looking for the best deal. "
                f"This {product['product_name']} is priced to move at "
                f"${product.get('suggested_price', product['price'])}. "
                f"It's already {product.get('discount_percentage', 20)}% off. "
                f"I can do ${float(product.get('suggested_price', product['price'])) * 0.95:.2f} "
                f"if you can pick up today."
            )
            
        elif inquiry_type == "availability":
            alternatives.append(
                f"Yes! Still available. Actually, we have {product.get('current_stock', 'several')} "
                f"units of this {product['product_name']} in stock. First come, first served!"
            )
            
        return alternatives
    
    def _suggest_follow_ups(
        self, 
        inquiry_type: str, 
        product: Dict[str, Any]
    ) -> List[str]:
        """Suggest follow-up actions based on inquiry type."""
        follow_ups = []
        
        if inquiry_type == "availability":
            follow_ups.extend([
                "Ask when they'd like to pick up",
                "Offer to hold item for 24 hours",
                "Mention any similar items available"
            ])
            
        elif inquiry_type == "price_negotiation":
            follow_ups.extend([
                "Ask about quantity needed",
                "Mention bulk discount tiers",
                "Suggest bundling with similar items"
            ])
            
        elif inquiry_type == "pickup_delivery":
            follow_ups.extend([
                "Provide specific pickup hours",
                "Offer delivery cost estimate",
                "Send location/parking details"
            ])
            
        return follow_ups
    
    def _format_product_details(self, product: Dict[str, Any]) -> str:
        """Format product details for inquiry response."""
        details = []
        
        if product.get('brand'):
            details.append(f"Brand: {product['brand']}")
        if product.get('condition'):
            details.append(f"Condition: {product['condition']}")
        if product.get('notes'):
            details.append(f"Notes: {product['notes']}")
            
        return "\n".join(details) if details else "Full specifications available on request" 