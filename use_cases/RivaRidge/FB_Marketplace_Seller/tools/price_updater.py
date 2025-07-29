"""Price updater tool for Facebook Marketplace listings."""

from typing import Dict, Any, List
from ice_sdk.tools.base import ToolBase


class PriceUpdaterTool(ToolBase):
    """Updates prices for Facebook Marketplace listings."""
    
    name: str = "price_updater"
    description: str = "Updates listing prices based on pricing recommendations"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        # Merge input_data with kwargs for flexibility
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(
        self,
        price_adjustments: List[Dict[str, Any]] = None,
        auto_update: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Update listing prices based on recommendations."""
        
        price_adjustments = price_adjustments or []
        
        if not price_adjustments:
            return {
                "success": True,
                "message": "No price adjustments to process",
                "updates_applied": 0,
                "updates_failed": 0,
                "total_value_change": 0.0
            }
        
        print(f"💰 Processing {len(price_adjustments)} price adjustments")
        
        successful_updates = []
        failed_updates = []
        total_value_change = 0.0
        
        for adjustment in price_adjustments:
            try:
                result = await self._update_single_price(adjustment, auto_update)
                if result["success"]:
                    successful_updates.append(result)
                    total_value_change += result["value_change"]
                else:
                    failed_updates.append(result)
            except Exception as e:
                failed_updates.append({
                    "item_id": adjustment.get("item_id", "unknown"),
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "updates_applied": len(successful_updates),
            "updates_failed": len(failed_updates),
            "total_adjustments": len(price_adjustments),
            "total_value_change": round(total_value_change, 2),
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "auto_update_enabled": auto_update
        }
    
    async def _update_single_price(
        self,
        adjustment: Dict[str, Any],
        auto_update: bool
    ) -> Dict[str, Any]:
        """Update price for a single listing."""
        
        item_id = adjustment.get("item_id", "unknown")
        current_price = adjustment.get("current_price", 0.0)
        recommended_price = adjustment.get("recommended_price", 0.0)
        reason = adjustment.get("reason", "No reason provided")
        
        print(f"🏷️  Updating {item_id}: ${current_price} → ${recommended_price}")
        print(f"📋 Reason: {reason}")
        
        # Simulate price update API call
        import asyncio
        import random
        await asyncio.sleep(0.2)  # Simulate API delay
        
        # Simulate update success/failure
        if auto_update:
            success_rate = 0.9  # 90% success for auto updates
        else:
            success_rate = 0.95  # 95% success for manual approval
        
        if random.random() < success_rate:
            # Successful update
            value_change = recommended_price - current_price
            
            # Simulate Facebook's response
            update_result = {
                "success": True,
                "item_id": item_id,
                "previous_price": current_price,
                "new_price": recommended_price,
                "value_change": value_change,
                "change_percent": ((recommended_price - current_price) / current_price) * 100 if current_price > 0 else 0,
                "update_timestamp": "2025-07-27T13:00:00Z",
                "facebook_listing_id": f"fb_listing_{item_id}",
                "status": "active",
                "reason": reason
            }
            
            print("✅ Price updated successfully")
            
        else:
            # Failed update
            failure_reasons = [
                "API rate limit exceeded",
                "Listing not found",
                "Price outside allowed range",
                "Network timeout"
            ]
            
            update_result = {
                "success": False,
                "item_id": item_id,
                "error": random.choice(failure_reasons),
                "attempted_price": recommended_price,
                "current_price": current_price,
                "value_change": 0.0
            }
            
            print(f"❌ Price update failed: {update_result['error']}")
        
        return update_result 