"""Inventory Analyzer Tool - Analyzes available inventory for listing."""

from typing import Dict, Any, List
from ice_core.base_tool import ToolBase


class InventoryAnalyzerTool(ToolBase):
    """Analyzes inventory items to determine what should be listed."""
    
    name: str = "inventory_analyzer"
    description: str = "Analyzes inventory to filter items suitable for marketplace listing"
    
    # Tool configuration
    min_value_threshold: float = 10.0
    condition_requirements: List[str] = ["New", "Like New", "Good", "Fair"]
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Analyze inventory and filter eligible items."""
        inventory = kwargs.get("inventory", [])
        config = kwargs.get("config", {})
        
        # Override defaults with config if provided
        min_value = config.get("min_value_threshold", self.min_value_threshold)
        conditions = config.get("condition_requirements", self.condition_requirements)
        
        eligible_items = []
        rejected_items = []
        total_value = 0.0
        
        for item in inventory:
            # Check condition requirements
            if item.get("condition") not in conditions:
                rejected_items.append({
                    "item": item,
                    "reason": f"Condition '{item.get('condition')}' not acceptable"
                })
                continue
                
            # Check value threshold
            estimated_value = self._estimate_resale_value(item)
            if estimated_value < min_value:
                rejected_items.append({
                    "item": item,
                    "reason": f"Estimated value ${estimated_value:.2f} below threshold"
                })
                continue
                
            # Item is eligible
            item["estimated_value"] = estimated_value
            eligible_items.append(item)
            total_value += estimated_value
            
        return {
            "eligible_items": eligible_items,
            "rejected_items": rejected_items,
            "total_value": total_value,
            "item_count": len(eligible_items)
        }
        
    def _estimate_resale_value(self, item: Dict[str, Any]) -> float:
        """Estimate resale value based on condition and original price."""
        original_price = item.get("original_price", 0)
        condition = item.get("condition", "Unknown")
        
        # Simple depreciation model
        condition_multipliers = {
            "New": 0.85,
            "Like New": 0.70,
            "Good": 0.50,
            "Fair": 0.30,
            "Poor": 0.15
        }
        
        multiplier = condition_multipliers.get(condition, 0.25)
        return original_price * multiplier
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool inputs."""
        return {
            "type": "object",
            "properties": {
                "inventory": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "condition": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "original_price": {"type": "number"}
                        },
                        "required": ["id", "name", "condition"]
                    }
                },
                "config": {
                    "type": "object",
                    "properties": {
                        "min_value_threshold": {"type": "number"},
                        "condition_requirements": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["inventory"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool outputs."""
        return {
            "type": "object",
            "properties": {
                "eligible_items": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "rejected_items": {
                    "type": "array", 
                    "items": {"type": "object"}
                },
                "total_value": {"type": "number"},
                "item_count": {"type": "integer"}
            },
            "required": ["eligible_items", "rejected_items", "total_value", "item_count"]
        } 