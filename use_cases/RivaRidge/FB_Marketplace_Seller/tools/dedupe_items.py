"""Deduplicate inventory items tool."""

from typing import Dict, Any, List
from ice_sdk.tools.base import ToolBase


class DedupeItemsTool(ToolBase):
    """Removes duplicate items from inventory based on SKU."""
    
    name: str = "dedupe_items"
    description: str = "Removes duplicate SKUs and filters sold items"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        # Merge input_data with kwargs for flexibility
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(self, clean_items: List[Dict], strategy: str = "keep_first", **kwargs) -> Dict[str, Any]:
        """Deduplicate items and remove sold inventory."""
        
        if not clean_items:
            return {
                "success": True,
                "items_before_dedup": 0,
                "items_after_dedup": 0,
                "duplicates_removed": 0,
                "clean_items": []
            }
        
        items_before = len(clean_items)
        seen_skus = set()
        deduplicated = []
        duplicates_removed = 0
        
        for item in clean_items:
            sku = item.get("sku", "")
            
            # Skip items with no quantity (sold out)
            if item.get("quantity", 0) <= 0:
                duplicates_removed += 1
                continue
            
            # Handle duplicates based on strategy
            if sku in seen_skus:
                if strategy == "keep_first":
                    duplicates_removed += 1
                    continue
                elif strategy == "merge_quantities":
                    # Find existing item and merge quantities
                    for existing in deduplicated:
                        if existing["sku"] == sku:
                            existing["quantity"] += item.get("quantity", 0)
                            break
                    duplicates_removed += 1
                    continue
            
            seen_skus.add(sku)
            deduplicated.append(item)
        
        return {
            "success": True,
            "items_before_dedup": items_before,
            "items_after_dedup": len(deduplicated),
            "duplicates_removed": duplicates_removed,
            "strategy_used": strategy,
            "clean_items": deduplicated
        } 