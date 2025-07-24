"""Listing Agent for orchestrating marketplace listing creation.

This agent manages the end-to-end process of creating optimized
marketplace listings while tracking costs and ensuring quality.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from ice_sdk.agents.agent_node import AgentNode
from ice_core.models import ModelProvider


class ListingAgent(AgentNode):
    """Orchestrates the creation of marketplace listings with cost optimization."""
    
    name: str = "marketplace_listing_agent"
    description: str = "Manages the complete listing creation process"
    model: str = "gpt-3.5-turbo"  # Using cheaper model for orchestration
    provider: ModelProvider = ModelProvider.OPENAI
    
    # Agent configuration
    system_prompt: str = """You are a Professional Marketplace Listing Specialist managing surplus inventory sales.
    
Your responsibilities:
1. Create high-quality, compelling listings that convert browsers to buyers
2. Write engaging descriptions that highlight value and create urgency
3. Ensure accuracy and full compliance with Facebook Marketplace policies
4. Optimize for search visibility and buyer engagement
5. Track performance metrics and suggest improvements

Focus on quality and conversion rate. Each listing should feel personalized and trustworthy."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cost_tracker = {
            "total_cost": 0.0,
            "total_tokens": 0,
            "items_processed": 0,
            "budget_remaining": 200.0  # $200 budget - no real constraints
        }
        
    async def process_inventory(
        self, 
        surplus_items: List[Dict[str, Any]],
        batch_size: int = 5
    ) -> Dict[str, Any]:
        """Process surplus inventory items into marketplace listings."""
        
        results = {
            "listings_created": [],
            "failed_items": [],
            "cost_summary": {},
            "recommendations": []
        }
        
        # Group items by category for efficient processing
        items_by_category = self._group_by_category(surplus_items)
        
        for category, items in items_by_category.items():
            # Process in batches to optimize LLM usage
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                
                # Check budget before processing
                if self.cost_tracker["budget_remaining"] < 0.10:
                    results["recommendations"].append(
                        f"Budget nearly exhausted. {len(items) - i} items not processed."
                    )
                    break
                
                # Process batch
                batch_results = await self._process_batch(batch, category)
                results["listings_created"].extend(batch_results["listings"])
                results["failed_items"].extend(batch_results.get("failed", []))
                
                # Update cost tracking
                self._update_cost_tracking(batch_results.get("cost", 0))
        
        # Generate summary
        results["cost_summary"] = self.cost_tracker
        results["recommendations"].extend(self._generate_final_recommendations(results))
        
        return results
    
    async def _process_batch(
        self, 
        items: List[Dict[str, Any]], 
        category: str
    ) -> Dict[str, Any]:
        """Process a batch of similar items."""
        
        batch_results = {
            "listings": [],
            "failed": [],
            "cost": 0.0
        }
        
        # For similar items, generate template once and reuse
        if len(items) > 1 and self._are_items_similar(items):
            template = await self._generate_category_template(category, items[0])
            
            for item in items:
                listing = await self._apply_template(template, item)
                batch_results["listings"].append(listing)
                batch_results["cost"] += listing.get("estimated_cost", 0)
        else:
            # Process individually
            for item in items:
                try:
                    listing = await self._create_listing(item)
                    batch_results["listings"].append(listing)
                    batch_results["cost"] += listing.get("estimated_cost", 0)
                except Exception as e:
                    batch_results["failed"].append({
                        "item": item,
                        "error": str(e)
                    })
        
        return batch_results
    
    async def _create_listing(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single listing using the listing generator tool."""
        
        # Use the listing generator tool
        from ice_sdk.tools.marketplace.listing_generator_tool import ListingGeneratorTool
        
        generator = ListingGeneratorTool()
        listing = await generator.execute(
            product=item,
            max_tokens_per_item=300  # Higher quality with increased budget
        )
        
        # Add quality score
        listing["quality_score"] = self._assess_listing_quality(listing)
        
        # Add posting priority
        listing["posting_priority"] = item.get("urgency_score", 50)
        
        return listing
    
    async def _generate_category_template(
        self, 
        category: str, 
        sample_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a reusable template for a category."""
        
        prompt = f"""Create a template description for {category} items with these characteristics:
- Condition variations: New, Open Box, Refurbished
- Price range: $20-$200
- Target audience: Individual consumers and small businesses

Template should have placeholders for: [PRODUCT_NAME], [BRAND], [CONDITION], [PRICE], [KEY_FEATURE]
Maximum 40 words."""

        # Use LLM to generate template
        response = await self.llm_generate(
            prompt=prompt,
            max_tokens=60,
            temperature=0.7
        )
        
        return {
            "category": category,
            "template": response,
            "estimated_cost": 0.002  # Rough estimate for template generation
        }
    
    async def _apply_template(
        self, 
        template: Dict[str, Any], 
        item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply template to create listing without additional LLM calls."""
        
        # Fill in template
        description = template["template"].replace("[PRODUCT_NAME]", item["product_name"])
        description = description.replace("[BRAND]", item["brand"])
        description = description.replace("[CONDITION]", item["condition"])
        description = description.replace("[PRICE]", f"${item['suggested_price']}")
        
        # Extract key feature
        key_feature = "Great Value"
        if item.get("discount_percentage", 0) > 30:
            key_feature = f"{int(item['discount_percentage'])}% OFF"
        
        description = description.replace("[KEY_FEATURE]", key_feature)
        
        # Create listing without LLM
        listing = {
            "sku": item["sku"],
            "title": f"{item['condition']} {item['brand']} {item['product_name']} - {key_feature}",
            "description": description,
            "price": item["suggested_price"],
            "category": item["category"],
            "condition": item["condition"],
            "estimated_cost": 0.0,  # No LLM cost for template application
            "template_used": True
        }
        
        return listing
    
    def _group_by_category(self, items: List[Dict[str, Any]]) -> Dict[str, List]:
        """Group items by category for batch processing."""
        grouped = {}
        for item in items:
            category = item.get("category", "Other")
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)
        return grouped
    
    def _are_items_similar(self, items: List[Dict[str, Any]]) -> bool:
        """Check if items are similar enough to use same template."""
        if len(items) < 2:
            return False
            
        # Check if same category and similar price range
        categories = set(item.get("category") for item in items)
        if len(categories) > 1:
            return False
            
        # Check price variance
        prices = [item.get("suggested_price", 0) for item in items]
        if max(prices) > min(prices) * 2:
            return False
            
        return True
    
    def _assess_listing_quality(self, listing: Dict[str, Any]) -> float:
        """Assess quality of generated listing (0-100)."""
        score = 50.0
        
        # Title quality
        title = listing.get("title", "")
        if len(title) > 20 and len(title) < 80:
            score += 10
        if any(word in title.lower() for word in ["new", "sale", "off", "deal"]):
            score += 10
            
        # Description quality
        description = listing.get("description", "")
        if len(description) > 50:
            score += 10
        if listing.get("features"):
            score += 10
            
        # Completeness
        required_fields = ["title", "description", "price", "category"]
        if all(listing.get(field) for field in required_fields):
            score += 10
            
        return min(score, 100)
    
    def _update_cost_tracking(self, cost: float):
        """Update cost tracking metrics."""
        self.cost_tracker["total_cost"] += cost
        self.cost_tracker["budget_remaining"] -= cost
        self.cost_tracker["items_processed"] += 1
        
        # Estimate tokens (rough)
        self.cost_tracker["total_tokens"] += int(cost * 500000)  # Rough estimate
    
    def _generate_final_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate final recommendations based on results."""
        recommendations = []
        
        # Cost efficiency
        avg_cost = (
            self.cost_tracker["total_cost"] / self.cost_tracker["items_processed"]
            if self.cost_tracker["items_processed"] > 0 else 0
        )
        if avg_cost < 0.01:
            recommendations.append(
                f"Excellent cost efficiency: ${avg_cost:.3f} per listing"
            )
        
        # Quality recommendations
        high_quality = [
            l for l in results["listings_created"] 
            if l.get("quality_score", 0) > 80
        ]
        if len(high_quality) > 0:
            recommendations.append(
                f"{len(high_quality)} high-quality listings ready for immediate posting"
            )
        
        # Posting strategy
        urgent_items = [
            l for l in results["listings_created"] 
            if l.get("posting_priority", 0) > 70
        ]
        if urgent_items:
            recommendations.append(
                f"Post {len(urgent_items)} urgent items first (high surplus score)"
            )
        
        return recommendations 