"""Inventory Analyzer Tool for identifying surplus items.

Analyzes inventory data to identify items that should be sold based on:
- Time in inventory
- Stock levels
- Category-specific rules
"""

from typing import Any, Dict, List, ClassVar
import pandas as pd
from pydantic import Field

from ice_core.base_tool import ToolBase


class InventoryAnalyzerTool(ToolBase):
    """Analyzes inventory to identify surplus items for marketplace listing."""
    
    name: str = "inventory_analyzer"
    description: str = "Analyzes inventory data to identify surplus items that should be sold"
    
    # Surplus criteria by category
    SURPLUS_RULES: ClassVar[Dict[str, Dict[str, int]]] = {
        "Electronics": {"months_threshold": 6, "stock_threshold": 30},
        "Furniture": {"months_threshold": 12, "stock_threshold": 5},
        "Kitchen": {"months_threshold": 8, "stock_threshold": 50},
        "Office": {"months_threshold": 9, "stock_threshold": 20},
        "Sports": {"months_threshold": 6, "stock_threshold": 40},
        "Garden": {"months_threshold": 10, "stock_threshold": 30},
        "Accessories": {"months_threshold": 12, "stock_threshold": 100},
        "default": {"months_threshold": 9, "stock_threshold": 25}
    }
    
    async def _execute_impl(
        self,
        file_path: str = Field(..., description="Path to inventory CSV file"),
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Analyze inventory and identify surplus items."""
        
        # Load inventory data
        df = pd.read_csv(file_path)
        
        surplus_items = []
        analysis_summary = {
            "total_items": len(df),
            "surplus_count": 0,
            "categories": {},
            "total_value": 0
        }
        
        # Analyze each item
        for _, item in df.iterrows():
            category = item['category']
            rules = self.SURPLUS_RULES.get(category, self.SURPLUS_RULES['default'])
            
            # Check if item qualifies as surplus
            is_surplus = (
                item['months_in_inventory'] >= rules['months_threshold'] or
                item['current_stock'] >= rules['stock_threshold']
            )
            
            if is_surplus:
                # Calculate suggested discount based on age and stock
                age_factor = min(item['months_in_inventory'] / 12, 1.0)
                stock_factor = min(item['current_stock'] / 100, 1.0)
                suggested_discount = 0.1 + (0.4 * age_factor) + (0.1 * stock_factor)
                suggested_price = item['original_price'] * (1 - suggested_discount)
                
                surplus_item = {
                    "sku": item['sku'],
                    "product_name": item['product_name'],
                    "category": category,
                    "brand": item['brand'],
                    "condition": item['condition'],
                    "original_price": item['original_price'],
                    "suggested_price": round(suggested_price, 2),
                    "discount_percentage": round(suggested_discount * 100, 1),
                    "current_stock": item['current_stock'],
                    "months_in_inventory": item['months_in_inventory'],
                    "location": item['location'],
                    "notes": item['notes'],
                    "surplus_reason": self._get_surplus_reason(item, rules),
                    "urgency_score": self._calculate_urgency(item)
                }
                
                surplus_items.append(surplus_item)
                
                # Update summary
                analysis_summary["surplus_count"] += 1
                analysis_summary["total_value"] += suggested_price * item['current_stock']
                
                if category not in analysis_summary["categories"]:
                    analysis_summary["categories"][category] = 0
                analysis_summary["categories"][category] += 1
        
        # Sort by urgency score
        surplus_items.sort(key=lambda x: x['urgency_score'], reverse=True)
        
        return {
            "surplus_items": surplus_items,
            "summary": analysis_summary,
            "recommendations": self._generate_recommendations(surplus_items, analysis_summary)
        }
    
    def _get_surplus_reason(self, item: pd.Series, rules: Dict[str, int]) -> str:
        """Determine why an item is marked as surplus."""
        reasons = []
        
        if item['months_in_inventory'] >= rules['months_threshold']:
            reasons.append(f"In inventory for {item['months_in_inventory']} months")
            
        if item['current_stock'] >= rules['stock_threshold']:
            reasons.append(f"High stock level ({item['current_stock']} units)")
            
        if item['condition'] != 'New':
            reasons.append(f"Condition: {item['condition']}")
            
        return " | ".join(reasons)
    
    def _calculate_urgency(self, item: pd.Series) -> float:
        """Calculate urgency score (0-100) for selling an item."""
        # Base score on age
        age_score = min(item['months_in_inventory'] * 5, 50)
        
        # Add score for stock levels
        stock_score = min(item['current_stock'] / 10, 30)
        
        # Boost for certain conditions
        condition_boost = {
            "Open Box": 10,
            "Refurbished": 15,
            "New": 0
        }.get(item['condition'], 5)
        
        # Category-specific boosts
        category_boost = {
            "Electronics": 10,  # Tech depreciates fast
            "Accessories": 5,   # Fashion/tech accessories lose relevance
            "Furniture": 0      # Furniture holds value better
        }.get(item['category'], 3)
        
        return min(age_score + stock_score + condition_boost + category_boost, 100)
    
    def _generate_recommendations(
        self, 
        surplus_items: List[Dict], 
        summary: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Overall recommendation
        if summary["surplus_count"] > 0:
            recommendations.append(
                f"Found {summary['surplus_count']} surplus items worth "
                f"${summary['total_value']:,.2f} in potential revenue"
            )
        
        # Category-specific recommendations
        top_categories = sorted(
            summary["categories"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        if top_categories:
            recommendations.append(
                f"Focus on {top_categories[0][0]} items first "
                f"({top_categories[0][1]} items)"
            )
        
        # Urgency-based recommendation
        urgent_items = [item for item in surplus_items if item['urgency_score'] > 70]
        if urgent_items:
            recommendations.append(
                f"{len(urgent_items)} items need immediate attention "
                f"(urgency score > 70)"
            )
        
        # Bulk sale recommendation
        high_stock_items = [
            item for item in surplus_items 
            if item['current_stock'] > 50
        ]
        if high_stock_items:
            recommendations.append(
                f"Consider bulk sales for {len(high_stock_items)} items "
                f"with 50+ units in stock"
            )
        
        return recommendations 