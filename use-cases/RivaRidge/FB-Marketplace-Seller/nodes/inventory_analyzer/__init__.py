"""Inventory Analyzer Node - Analyzes available inventory for listing."""

from typing import Dict, Any, List
from pydantic import Field, ConfigDict
from ice_core.base_node import BaseNode
from ice_core.models.node_models import NodeExecutionResult


class InventoryAnalyzerNode(BaseNode):
    """Analyzes inventory items to determine what should be listed."""
    
    model_config = ConfigDict(extra="forbid")
    
    # Configuration fields
    min_value_threshold: float = Field(
        default=10.0,
        description="Minimum item value to consider for listing"
    )
    
    condition_requirements: List[str] = Field(
        default=["New", "Like New", "Good", "Fair"],
        description="Acceptable item conditions for listing"
    )
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Define expected inputs."""
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
                }
            },
            "required": ["inventory"]
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """Define output schema."""
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
            }
        }
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze inventory and filter eligible items."""
        inventory = inputs.get("inventory", [])
        
        eligible_items = []
        rejected_items = []
        total_value = 0.0
        
        for item in inventory:
            # Check condition requirements
            if item.get("condition") not in self.condition_requirements:
                rejected_items.append({
                    "item": item,
                    "reason": f"Condition '{item.get('condition')}' not acceptable"
                })
                continue
                
            # Check value threshold
            estimated_value = self._estimate_resale_value(item)
            if estimated_value < self.min_value_threshold:
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