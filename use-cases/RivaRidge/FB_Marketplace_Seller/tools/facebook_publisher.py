"""Facebook Marketplace publishing tool."""

from typing import Dict, Any, List
import time
import random
from ice_sdk.tools.base import ToolBase


class FacebookPublisherTool(ToolBase):
    """Publishes enriched items to Facebook Marketplace (simulated)."""
    
    name: str = "facebook_publisher"
    description: str = "Publishes product listings to Facebook Marketplace"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        # Merge input_data with kwargs for flexibility
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(self, enriched_items: List[Dict], auto_publish: bool = True, **kwargs) -> Dict[str, Any]:
        """Publish items to Facebook Marketplace."""
        
        if not enriched_items:
            return {
                "success": True,
                "items_published": 0,
                "items_failed": 0,
                "listings": []
            }
        
        published_listings = []
        failed_count = 0
        
        for item in enriched_items:
            try:
                # Simulate API call delay
                await self._simulate_api_delay()
                
                # Create Facebook listing
                listing = self._create_facebook_listing(item)
                
                # Simulate publish (90% success rate)
                if random.random() < 0.9:
                    listing["status"] = "published"
                    listing["listing_id"] = f"FB_{int(time.time())}_{random.randint(1000, 9999)}"
                    listing["marketplace_url"] = f"https://facebook.com/marketplace/item/{listing['listing_id']}"
                    published_listings.append(listing)
                else:
                    listing["status"] = "failed"
                    listing["error"] = "API rate limit exceeded"
                    published_listings.append(listing)
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                published_listings.append({
                    "sku": item.get("sku", "unknown"),
                    "status": "failed",
                    "error": str(e)
                })
        
        # Calculate estimated reach and value
        successful_listings = [l for l in published_listings if l["status"] == "published"]
        estimated_reach = len(successful_listings) * random.randint(50, 200)
        total_value = sum(l.get("price", 0) for l in successful_listings)
        
        return {
            "success": True,
            "items_published": len(successful_listings),
            "items_failed": failed_count,
            "total_items": len(enriched_items),
            "estimated_reach": estimated_reach,
            "total_estimated_value": total_value,
            "listings": published_listings,
            "platform": "facebook_marketplace"
        }
    
    async def _simulate_api_delay(self):
        """Simulate realistic API call delay."""
        import asyncio
        delay = random.uniform(0.1, 0.5)  # 100-500ms delay
        await asyncio.sleep(delay)
    
    def _create_facebook_listing(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Facebook Marketplace listing from enriched item."""
        
        # Use optimized content if available, otherwise fall back to original
        title = item.get("optimized_title", item.get("name", "Untitled Item"))
        description = item.get("optimized_description", item.get("description", "No description available"))
        
        listing = {
            "sku": item.get("sku"),
            "title": title[:80],  # Facebook title limit
            "description": description,
            "price": item.get("price", 0),
            "condition": item.get("condition", "Used"),
            "category": self._map_to_facebook_category(item.get("marketplace_category", item.get("category", "Other"))),
            "location": item.get("location", "San Francisco, CA"),
            "images": self._get_item_images(item),
            "keywords": item.get("suggested_keywords", []),
            "brand": item.get("brand", ""),
            "availability": "available" if item.get("quantity", 0) > 0 else "sold",
            "created_at": time.time()
        }
        
        return listing
    
    def _map_to_facebook_category(self, category: str) -> str:
        """Map general category to Facebook Marketplace category."""
        
        category_mapping = {
            "electronics": "Electronics",
            "clothing": "Clothing & Accessories", 
            "furniture": "Home & Garden",
            "books": "Entertainment",
            "toys": "Family",
            "tools": "Home & Garden",
            "sports": "Sports & Outdoors",
            "automotive": "Vehicles",
            "jewelry": "Clothing & Accessories",
            "appliances": "Home & Garden"
        }
        
        return category_mapping.get(category.lower(), "Other")
    
    def _get_item_images(self, item: Dict[str, Any]) -> List[str]:
        """Get or generate placeholder images for the item."""
        
        # In a real implementation, this would handle actual image URLs
        images = []
        
        # Check if item has image paths
        if "images" in item and item["images"]:
            images = item["images"]
        else:
            # Generate placeholder image URL based on category
            category = item.get("category", "general")
            placeholder_url = f"https://placeholder.images/{category.lower()}/600x400"
            images = [placeholder_url]
        
        return images[:5]  # Facebook allows max 5 images 