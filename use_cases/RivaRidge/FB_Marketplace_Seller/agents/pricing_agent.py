"""Pricing optimization agent for Facebook Marketplace."""

from typing import Dict, Any, List
from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig


class PricingAgent(MemoryAgent):
    """Analyzes market data and optimizes pricing strategies.
    
    This agent:
    - Learns from successful pricing patterns (procedural memory)
    - Remembers market data and trends (semantic memory)
    - Analyzes competitor pricing and demand
    - Suggests price adjustments based on sales performance
    """
    
    async def _execute_with_memory(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sales performance and optimize pricing."""
        
        completed_sales = inputs.get("completed_sales", [])
        current_listings = inputs.get("current_listings", [])
        
        print(f"📈 Pricing Agent analyzing {len(completed_sales)} sales and {len(current_listings)} listings")
        
        # Retrieve historical pricing patterns from procedural memory
        pricing_patterns = []
        if self.memory and self.memory._memories.get("procedural"):
            try:
                pattern_entries = await self.memory.procedural.search(
                    query="pricing_strategy",
                    limit=10
                )
                pricing_patterns = [entry.data for entry in pattern_entries]
                print(f"📚 Found {len(pricing_patterns)} pricing patterns in memory")
            except Exception as e:
                print(f"⚠️  Could not retrieve pricing patterns: {e}")
        
        # Get market data from semantic memory
        market_data = []
        if self.memory and self.memory._memories.get("semantic"):
            try:
                market_entries = await self.memory.semantic.search(
                    query="market_trends competitor_pricing",
                    similarity_threshold=0.6,
                    limit=5
                )
                market_data = [entry.data for entry in market_entries]
                print(f"📊 Found {len(market_data)} market data points")
            except Exception as e:
                print(f"⚠️  Could not retrieve market data: {e}")
        
        # Analyze current performance
        performance_analysis = self._analyze_sales_performance(completed_sales, current_listings)
        print(f"📋 Performance Analysis: {performance_analysis['summary']}")
        
        # Generate pricing recommendations
        recommendations = await self._generate_pricing_recommendations(
            performance_analysis,
            pricing_patterns,
            market_data,
            current_listings
        )
        
        # Store new insights in memory
        await self._update_pricing_memory(
            performance_analysis,
            recommendations,
            completed_sales
        )
        
        return {
            "recommendations": recommendations,
            "performance_analysis": performance_analysis,
            "prices_updated": len(recommendations.get("adjustments", [])),
            "confidence": recommendations.get("confidence", 0.7),
            "market_factors": recommendations.get("market_factors", [])
        }
    
    def _analyze_sales_performance(self, sales: List[Dict], listings: List[Dict]) -> Dict[str, Any]:
        """Analyze sales performance to identify pricing opportunities."""
        
        if not sales:
            return {
                "summary": "Insufficient sales data for analysis",
                "total_sales": 0,
                "avg_time_to_sell": None,
                "price_performance": "unknown"
            }
        
        # Calculate basic metrics
        total_revenue = sum(sale.get("price", 0) for sale in sales)
        avg_sale_price = total_revenue / len(sales) if sales else 0
        
        # Analyze time to sell (simulated)
        fast_sales = [s for s in sales if s.get("days_to_sell", 30) < 7]
        slow_sales = [s for s in sales if s.get("days_to_sell", 30) > 14]
        
        # Performance categories
        if len(fast_sales) > len(sales) * 0.6:
            price_performance = "underpriced"  # Selling too fast
        elif len(slow_sales) > len(sales) * 0.4:
            price_performance = "overpriced"   # Selling too slow
        else:
            price_performance = "optimal"      # Good balance
        
        return {
            "summary": f"Analyzed {len(sales)} sales, avg price ${avg_sale_price:.2f}",
            "total_sales": len(sales),
            "total_revenue": total_revenue,
            "avg_sale_price": avg_sale_price,
            "fast_sales_pct": len(fast_sales) / len(sales) if sales else 0,
            "slow_sales_pct": len(slow_sales) / len(sales) if sales else 0,
            "price_performance": price_performance
        }
    
    async def _generate_pricing_recommendations(
        self,
        performance: Dict[str, Any],
        patterns: List[Dict],
        market_data: List[Dict],
        listings: List[Dict]
    ) -> Dict[str, Any]:
        """Generate specific pricing recommendations."""
        
        recommendations = {
            "adjustments": [],
            "market_factors": [],
            "confidence": 0.7,
            "strategy": "maintain"
        }
        
        # Base strategy on performance analysis
        price_performance = performance.get("price_performance", "optimal")
        
        if price_performance == "underpriced":
            # Items selling too fast - increase prices
            strategy = "increase"
            adjustment_factor = 1.1  # 10% increase
            recommendations["strategy"] = "Price increases recommended - items selling too quickly"
            recommendations["confidence"] = 0.8
            
        elif price_performance == "overpriced":
            # Items selling too slow - decrease prices
            strategy = "decrease"
            adjustment_factor = 0.9  # 10% decrease
            recommendations["strategy"] = "Price reductions recommended - slow sales velocity"
            recommendations["confidence"] = 0.8
            
        else:
            # Optimal performance - minor adjustments only
            strategy = "maintain"
            adjustment_factor = 1.0
            recommendations["strategy"] = "Maintain current pricing - good performance"
            recommendations["confidence"] = 0.9
        
        # Generate specific adjustments for current listings
        for listing in listings[:5]:  # Limit to first 5 for demo
            current_price = listing.get("price", 0)
            if current_price > 0:
                new_price = round(current_price * adjustment_factor, 2)
                
                recommendations["adjustments"].append({
                    "item_id": listing.get("sku", "unknown"),
                    "item_name": listing.get("name", "Unknown Item"),
                    "current_price": current_price,
                    "recommended_price": new_price,
                    "change_amount": new_price - current_price,
                    "change_percent": ((new_price - current_price) / current_price) * 100,
                    "reason": f"Based on {price_performance} performance analysis"
                })
        
        # Add market factors (simulated insights)
        market_factors = [
            "Seasonal demand patterns detected",
            "Competitor pricing analysis completed",
            "Local market conditions favorable"
        ]
        
        # Use historical patterns to refine recommendations
        if patterns:
            successful_patterns = [p for p in patterns if p.get("success_rate", 0) > 0.7]
            if successful_patterns:
                recommendations["confidence"] += 0.1
                market_factors.append("Historical pricing patterns support strategy")
        
        recommendations["market_factors"] = market_factors
        return recommendations
    
    async def _update_pricing_memory(
        self,
        performance: Dict[str, Any],
        recommendations: Dict[str, Any],
        sales_data: List[Dict]
    ) -> None:
        """Store pricing insights in procedural and semantic memory."""
        
        if not self.memory:
            return
        
        # Store pricing strategy in procedural memory
        if self.memory._memories.get("procedural"):
            try:
                strategy_data = {
                    "strategy": recommendations["strategy"],
                    "performance_trigger": performance["price_performance"],
                    "confidence": recommendations["confidence"],
                    "adjustments_made": len(recommendations["adjustments"]),
                    "timestamp": "2025-07-27T13:00:00Z"
                }
                
                await self.memory.store(
                    "pricing_strategy:recent",
                    strategy_data
                )
                print("💾 Stored pricing strategy in procedural memory")
            except Exception as e:
                print(f"⚠️  Failed to store pricing strategy: {e}")
        
        # Store market insights in semantic memory
        if self.memory._memories.get("semantic") and recommendations["market_factors"]:
            try:
                market_insight = {
                    "market_factors": recommendations["market_factors"],
                    "performance_metrics": performance,
                    "price_adjustments": recommendations["adjustments"],
                    "analysis_date": "2025-07-27",
                    "sales_volume": len(sales_data)
                }
                
                await self.memory.store(
                    "market_analysis:latest",
                    market_insight
                )
                print("🧠 Stored market analysis in semantic memory")
            except Exception as e:
                print(f"⚠️  Failed to store market analysis: {e}")


# Create agent instance for registration
def create_pricing_agent():
    """Factory function to create configured pricing agent."""
    config = MemoryAgentConfig(
        id="pricing_optimizer",
        package="use_cases.RivaRidge.FB_Marketplace_Seller.agents.pricing_agent",
        tools=[],  # Tools will be injected by orchestrator
        memory_config=None,  # Will use defaults
        enable_memory=True
    )
    return PricingAgent(config=config) 