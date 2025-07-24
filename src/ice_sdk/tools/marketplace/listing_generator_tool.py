"""Listing Generator Tool for creating marketplace listings.

Generates compelling titles and descriptions for marketplace listings
while being mindful of token usage and budget constraints.
"""

from typing import Any, Dict, ClassVar, List, Optional
from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_sdk.providers.llm_service import LLMService


class ListingGeneratorTool(ToolBase):
    """Generates optimized marketplace listings with budget-conscious LLM usage."""
    
    name: str = "listing_generator"
    description: str = "Creates compelling marketplace titles and descriptions"
    
    # Templates to reduce token usage
    TITLE_TEMPLATES: ClassVar[Dict[str, str]] = {
        "Electronics": "{condition} {brand} {product} - {key_feature}",
        "Furniture": "{product} - {brand} {key_feature} {condition}",
        "Kitchen": "{brand} {product} Set - {condition}",
        "Office": "Professional {product} by {brand} - {condition}",
        "default": "{brand} {product} - {condition} {key_feature}"
    }
    
    # Enhanced prompt template for better quality
    DESCRIPTION_PROMPT: ClassVar[str] = """Create a compelling Facebook Marketplace listing description for this item:

Product: {product_name}
Category: {category}
Brand: {brand}
Condition: {condition}
Price: ${price}
Original Price: ${original_price}
Discount: {discount}%
Key info: {notes}

Write a 100-150 word description that:
1. Highlights the value proposition and savings
2. Describes the condition accurately
3. Mentions key features and benefits
4. Creates urgency (limited stock, great deal, etc.)
5. Ends with a call to action

Be friendly, trustworthy, and conversational - like a neighbor selling to a neighbor."""

    async def _execute_impl(
        self,
        product: Dict[str, Any] = Field(..., description="Product details from inventory"),
        batch_mode: bool = Field(False, description="Process multiple similar items together"),
        max_tokens_per_item: int = Field(100, description="Token limit per item"),
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generate listing title and description."""
        
        # Generate title using template (no LLM needed)
        title = self._generate_title(product)
        
        # Generate description using LLM with better quality
        llm_service = LLMService()
        
        # Use GPT-4 for better quality since budget allows
        description = await llm_service.generate(
            prompt=self.DESCRIPTION_PROMPT.format(
                product_name=product['product_name'],
                category=product['category'],
                brand=product['brand'],
                condition=product['condition'],
                price=product['suggested_price'],
                original_price=product.get('original_price', product['suggested_price'] * 1.5),
                discount=product.get('discount_percentage', 30),
                notes=product.get('notes', 'N/A')
            ),
            model="gpt-4",
            max_tokens=max_tokens_per_item * 3,  # Allow more tokens for better descriptions
            temperature=0.7
        )
        
        # Extract key features for bullet points (no LLM)
        features = self._extract_features(product)
        
        # Calculate estimated token usage
        estimated_tokens = len(description.split()) * 1.3  # Rough estimate
        estimated_cost = estimated_tokens * 0.002 / 1000  # GPT-3.5 pricing
        
        listing = {
            "sku": product['sku'],
            "title": title,
            "description": description.strip(),
            "features": features,
            "price": product['suggested_price'],
            "category": product['category'],
            "condition": product['condition'],
            "location": product.get('location', 'Local pickup available'),
            "estimated_tokens": int(estimated_tokens),
            "estimated_cost": round(estimated_cost, 4),
            "marketplace_ready": True
        }
        
        # Add Facebook Marketplace specific formatting
        listing["fb_marketplace_format"] = self._format_for_facebook(listing)
        
        return listing
    
    def _generate_title(self, product: Dict[str, Any]) -> str:
        """Generate title using templates (no LLM needed)."""
        template = self.TITLE_TEMPLATES.get(
            product['category'], 
            self.TITLE_TEMPLATES['default']
        )
        
        # Extract key feature from product name or notes
        key_feature = self._extract_key_feature(product)
        
        title = template.format(
            condition=product['condition'],
            brand=product['brand'],
            product=self._simplify_product_name(product['product_name']),
            key_feature=key_feature
        )
        
        # Ensure title isn't too long for marketplace
        if len(title) > 80:
            title = title[:77] + "..."
            
        return title
    
    def _extract_key_feature(self, product: Dict[str, Any]) -> str:
        """Extract the most important feature from product info."""
        product_name = product['product_name'].lower()
        
        # Common features to highlight
        feature_keywords = {
            "wireless": "Wireless",
            "bluetooth": "Bluetooth",
            "rgb": "RGB",
            "1080p": "1080p HD",
            "4k": "4K",
            "ergonomic": "Ergonomic",
            "adjustable": "Adjustable",
            "portable": "Portable",
            "premium": "Premium",
            "pro": "Professional",
            "gaming": "Gaming",
            "smart": "Smart"
        }
        
        for keyword, feature in feature_keywords.items():
            if keyword in product_name:
                return feature
                
        # Fallback to discount if significant
        if product.get('discount_percentage', 0) > 30:
            return f"{int(product['discount_percentage'])}% OFF"
            
        return "Great Deal"
    
    def _simplify_product_name(self, name: str) -> str:
        """Simplify product name for title."""
        # Remove common redundant words
        redundant = ['with', 'and', 'for', 'the', '-']
        words = name.split()
        simplified = [w for w in words if w.lower() not in redundant]
        return ' '.join(simplified[:4])  # Keep it short
    
    def _extract_features(self, product: Dict[str, Any]) -> List[str]:
        """Extract bullet point features without LLM."""
        features = []
        
        # Condition feature
        if product['condition'] == 'New':
            features.append("✓ Brand new, unopened")
        elif product['condition'] == 'Open Box':
            features.append("✓ Open box - fully tested")
        elif product['condition'] == 'Refurbished':
            features.append("✓ Professionally refurbished")
            
        # Price feature
        if product.get('discount_percentage', 0) > 20:
            features.append(
                f"✓ {int(product['discount_percentage'])}% off retail price"
            )
            
        # Stock feature for bulk buyers
        if product.get('current_stock', 0) > 10:
            features.append("✓ Bulk quantities available")
            
        # Category-specific features
        if product['category'] == 'Electronics':
            features.append("✓ All accessories included")
        elif product['category'] == 'Furniture':
            features.append("✓ Easy assembly")
            
        return features[:3]  # Limit to 3 features
    
    def _format_for_facebook(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """Format listing for Facebook Marketplace requirements."""
        return {
            "title": listing['title'],
            "price": f"${listing['price']}",
            "category": self._map_to_fb_category(listing['category']),
            "condition": listing['condition'],
            "description": f"{listing['description']}\n\n" + 
                          "\n".join(listing['features']),
            "location": listing['location'],
            "availability": "In stock"
        }
    
    def _map_to_fb_category(self, category: str) -> str:
        """Map our categories to Facebook Marketplace categories."""
        mapping = {
            "Electronics": "Electronics",
            "Furniture": "Furniture", 
            "Kitchen": "Home & Garden",
            "Office": "Office Supplies",
            "Sports": "Sporting Goods",
            "Garden": "Home & Garden",
            "Accessories": "Electronics"
        }
        return mapping.get(category, "General") 