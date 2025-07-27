"""Marketplace Agent - Creates optimized marketplace listings."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ice_orchestrator.agent import AgentNode
from ice_core.models.node_models import AgentNodeConfig
from ice_core.models.llm import LLMConfig
from ice_core.models.enums import ModelProvider


class MarketplaceAgent(AgentNode):
    """Agent that creates optimized marketplace listings.
    
    This agent analyzes item data and market conditions to create
    compelling listings that maximize visibility and conversion.
    """
    
    def __init__(self):
        """Initialize the marketplace agent."""
        config = AgentNodeConfig(
            id="marketplace_agent",
            type="agent",
            package="ice_sdk.agents.marketplace_agent",  # Self-reference
            max_retries=3,
            tools=["facebook_api", "price_research", "image_enhancer"],
            system_prompt=self._get_system_prompt(),
            llm_config=LLMConfig(
                model="gpt-4",
                provider=ModelProvider.OPENAI,
                temperature=0.7,
                max_tokens=2000
            )
        )
        super().__init__(config=config)
        
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the marketplace agent."""
        return """You are a Professional Facebook Marketplace Listing Specialist.

Your role is to create compelling, high-converting marketplace listings that:
1. Grab attention with optimized titles
2. Provide detailed, honest descriptions
3. Use psychological pricing strategies
4. Highlight key selling points
5. Create urgency without being pushy

Guidelines:
- Be honest and transparent about item conditions
- Use keywords that buyers search for
- Price competitively based on market research
- Write in a friendly, conversational tone
- Include all relevant details buyers need

You have access to these tools:
- facebook_api: Create and manage marketplace listings
- price_research: Research competitive pricing
- image_enhancer: Enhance product images

Focus on creating listings that build trust and convert browsers into buyers."""

    async def _execute_agent_cycle(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's listing creation cycle.
        
        This method is called by the base AgentNode class.
        The actual tool execution is handled by the orchestrator's AgentExecutor.
        """
        # Extract inputs from workflow context
        item_data = inputs.get("item_data", [])
        pricing_data = inputs.get("pricing_data", [])
        image_data = inputs.get("image_data", [])
        
        # The agent executor will use tools to create listings
        # This is the high-level output structure
        
        # Simulate creating listings for each item
        created_listings = []
        active_listings = []
        
        for i, item in enumerate(item_data):
            # Find corresponding pricing and image data
            pricing = next((p for p in pricing_data if p["item_id"] == item["id"]), {})
            images = next((img for img in image_data if img["item_id"] == item["id"]), {})
            
            listing = {
                "listing_id": f"fb_listing_{item['id']}",
                "item_id": item["id"],
                "title": f"{item['name']} - {item['condition']} Condition",
                "price": pricing.get("suggested_price", item.get("estimated_value", 0)),
                "primary_image": images.get("primary_image"),
                "status": "active",
                "created_at": datetime.now().isoformat()
            }
            
            created_listings.append(listing)
            active_listings.append({
                "listing_id": listing["listing_id"],
                "item_name": item["name"],
                "price": listing["price"]
            })
        
        return {
            "task": "create_listing",
            "created_listings": created_listings,
            "active_listings": active_listings,  # This will be used by the loop
            "summary": {
                "total_created": len(created_listings),
                "total_value": sum(l["price"] for l in created_listings),
                "status": "success"
            }
        }


# Create a factory function for the registry
def create_marketplace_agent() -> MarketplaceAgent:
    """Factory function to create marketplace agent instances."""
    return MarketplaceAgent() 