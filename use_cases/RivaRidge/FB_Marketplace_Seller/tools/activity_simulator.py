"""Realistic marketplace activity simulator for demo purposes."""

import asyncio
import random
from datetime import datetime
from typing import Dict, Any, List
from ice_sdk.tools.base import ToolBase


class ActivitySimulatorTool(ToolBase):
    """Simulates realistic marketplace activities like messages, sales, and market events."""
    
    name: str = "activity_simulator"
    description: str = "Generates realistic marketplace activities for demonstration"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(
        self,
        activity_type: str = "all",
        duration_minutes: int = 5,
        listings: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Simulate realistic marketplace activities."""
        
        listings = listings or []
        
        print(f"🎭 Starting {duration_minutes}-minute marketplace activity simulation...")
        print(f"📊 Monitoring {len(listings)} active listings")
        
        if activity_type == "customer_messages":
            return await self._simulate_customer_messages(listings, duration_minutes)
        elif activity_type == "sales_events":
            return await self._simulate_sales_events(listings, duration_minutes)
        elif activity_type == "market_changes":
            return await self._simulate_market_changes(listings, duration_minutes)
        elif activity_type == "all":
            return await self._simulate_all_activities(listings, duration_minutes)
        else:
            return {"success": False, "error": f"Unknown activity type: {activity_type}"}
    
    async def _simulate_customer_messages(self, listings: List[Dict], duration: int) -> Dict[str, Any]:
        """Simulate realistic customer inquiries and messages."""
        
        print(f"💬 Simulating customer messages for {duration} minutes...")
        
        # Realistic customer inquiry templates
        inquiry_templates = [
            "Hi! Is the {item} still available? What's the condition like?",
            "Can you deliver to {location}? How much would shipping cost?", 
            "Would you accept ${price} for the {item}? I can pick up today.",
            "Is this {item} still under warranty? Any issues with it?",
            "Hi, I'm interested in the {item}. Can I see more photos?",
            "What's the lowest price you'd take for the {item}?",
            "Does the {item} come with all original accessories?",
            "Can I test the {item} before buying? I'm local.",
            "Hi! My friend recommended you. Is the {item} negotiable?",
            "How long have you had this {item}? Why are you selling?"
        ]
        
        customer_names = [
            "Sarah Johnson", "Mike Chen", "Jessica Rodriguez", "David Kim",
            "Amanda Thompson", "Carlos Martinez", "Emily Davis", "James Wilson",
            "Lisa Anderson", "Ryan O'Connor", "Maria Gonzalez", "Alex Park"
        ]
        
        locations = [
            "downtown Seattle", "Bellevue", "Capitol Hill", "Fremont",
            "Queen Anne", "Ballard", "Georgetown", "University District"
        ]
        
        messages = []
        total_inquiries = random.randint(3, 8)  # Realistic message volume
        
        for i in range(total_inquiries):
            # Select random listing and template
            if not listings:
                continue
                
            listing = random.choice(listings)
            template = random.choice(inquiry_templates)
            customer = random.choice(customer_names)
            location = random.choice(locations)
            
            # Generate realistic negotiation price (80-95% of listing price)
            listing_price = listing.get("price", 100)
            negotiation_price = int(listing_price * random.uniform(0.8, 0.95))
            
            # Fill template
            message = template.format(
                item=listing.get("title", listing.get("name", "item")).lower(),
                location=location,
                price=negotiation_price
            )
            
            # Create realistic message
            customer_message = {
                "message_id": f"msg_{i+1:03d}",
                "customer_name": customer,
                "customer_id": f"customer_{hash(customer) % 10000}",
                "item_sku": listing.get("sku", "unknown"),
                "item_title": listing.get("title", listing.get("name", "Unknown Item")),
                "inquiry": message,
                "timestamp": datetime.now().isoformat(),
                "message_type": self._classify_message_type(message),
                "urgency": random.choice(["low", "medium", "high"]),
                "customer_history": random.choice(["new", "returning", "frequent"])
            }
            
            messages.append(customer_message)
            
            print(f"📱 {customer}: {message[:50]}...")
            
            # Realistic timing between messages
            await asyncio.sleep(random.uniform(0.2, 0.8))
        
        return {
            "success": True,
            "activity_type": "customer_messages",
            "total_messages": len(messages),
            "messages": messages,
            "simulation_duration": duration,
            "message_rate": len(messages) / max(duration, 1)
        }
    
    async def _simulate_sales_events(self, listings: List[Dict], duration: int) -> Dict[str, Any]:
        """Simulate realistic sales transactions."""
        
        print(f"💰 Simulating sales events for {duration} minutes...")
        
        sales_events = []
        
        # Realistic sales rate (1-3 sales per simulation)
        num_sales = random.randint(1, min(3, len(listings)))
        
        for i in range(num_sales):
            if not listings:
                break
                
            listing = random.choice(listings)
            
            # Realistic sale scenarios
            sale_scenarios = [
                {"price_adjustment": 1.0, "reason": "full_price", "negotiation": False},
                {"price_adjustment": 0.95, "reason": "minor_negotiation", "negotiation": True},
                {"price_adjustment": 0.90, "reason": "quick_sale", "negotiation": True},
                {"price_adjustment": 0.85, "reason": "bulk_discount", "negotiation": True},
            ]
            
            scenario = random.choice(sale_scenarios)
            listing_price = listing.get("price", 100)
            sale_price = round(listing_price * scenario["price_adjustment"], 2)
            
            # Create realistic sale event
            sale_event = {
                "sale_id": f"sale_{i+1:03d}",
                "item_sku": listing.get("sku", "unknown"),
                "item_title": listing.get("title", listing.get("name", "Unknown Item")),
                "listing_price": listing_price,
                "sale_price": sale_price,
                "price_difference": sale_price - listing_price,
                "negotiated": scenario["negotiation"],
                "reason": scenario["reason"],
                "customer_id": f"buyer_{random.randint(1000, 9999)}",
                "sale_method": random.choice(["pickup", "delivery", "shipped"]),
                "payment_method": random.choice(["cash", "venmo", "paypal", "zelle"]),
                "days_to_sell": random.randint(1, 14),
                "timestamp": datetime.now().isoformat(),
                "feedback_rating": random.randint(4, 5)  # Most marketplace sales are positive
            }
            
            sales_events.append(sale_event)
            
            print(f"🎉 SALE: {listing.get('name', 'Item')} sold for ${sale_price}")
            
            # Remove from available listings (sold)
            listings.remove(listing)
            
            await asyncio.sleep(random.uniform(1.0, 2.0))
        
        return {
            "success": True,
            "activity_type": "sales_events", 
            "total_sales": len(sales_events),
            "sales": sales_events,
            "total_revenue": sum(sale["sale_price"] for sale in sales_events),
            "avg_sale_price": sum(sale["sale_price"] for sale in sales_events) / max(len(sales_events), 1),
            "simulation_duration": duration
        }
    
    async def _simulate_market_changes(self, listings: List[Dict], duration: int) -> Dict[str, Any]:
        """Simulate realistic market condition changes."""
        
        print(f"📈 Simulating market changes for {duration} minutes...")
        
        market_events = []
        
        # Market event types
        event_types = [
            {
                "type": "competitor_price_drop",
                "description": "Competitor lowered prices by 10%",
                "impact": "negative",
                "price_effect": -0.1
            },
            {
                "type": "seasonal_demand_increase", 
                "description": "Seasonal demand spike for electronics",
                "impact": "positive",
                "price_effect": 0.15
            },
            {
                "type": "supply_shortage",
                "description": "Supply chain issues affecting availability", 
                "impact": "positive",
                "price_effect": 0.08
            },
            {
                "type": "new_model_release",
                "description": "Newer model released, affecting demand",
                "impact": "negative", 
                "price_effect": -0.12
            },
            {
                "type": "positive_review_surge",
                "description": "Product featured in popular review",
                "impact": "positive",
                "price_effect": 0.05
            }
        ]
        
        # Generate 1-2 market events
        num_events = random.randint(1, 2)
        
        for i in range(num_events):
            event = random.choice(event_types)
            
            # Affect random subset of listings
            affected_listings = random.sample(
                listings, 
                min(random.randint(1, 3), len(listings))
            )
            
            market_event = {
                "event_id": f"market_{i+1:03d}",
                "event_type": event["type"],
                "description": event["description"],
                "impact": event["impact"],
                "price_effect": event["price_effect"],
                "affected_skus": [listing.get("sku") for listing in affected_listings],
                "affected_categories": list(set(listing.get("category", "unknown") for listing in affected_listings)),
                "timestamp": datetime.now().isoformat(),
                "duration_hours": random.randint(12, 72),
                "confidence": random.uniform(0.7, 0.95)
            }
            
            market_events.append(market_event)
            
            print(f"📊 MARKET EVENT: {event['description']}")
            print(f"   Impact: {event['impact']} ({event['price_effect']:+.1%})")
            print(f"   Affected: {len(affected_listings)} listings")
            
            await asyncio.sleep(random.uniform(0.5, 1.0))
        
        return {
            "success": True,
            "activity_type": "market_changes",
            "total_events": len(market_events),
            "events": market_events,
            "simulation_duration": duration
        }
    
    async def _simulate_all_activities(self, listings: List[Dict], duration: int) -> Dict[str, Any]:
        """Simulate all types of marketplace activities concurrently."""
        
        print(f"🎪 Simulating complete marketplace ecosystem for {duration} minutes...")
        
        # Run different activity types concurrently
        results = await asyncio.gather(
            self._simulate_customer_messages(listings.copy(), duration // 3),
            self._simulate_sales_events(listings.copy(), duration // 3), 
            self._simulate_market_changes(listings.copy(), duration // 3)
        )
        
        messages_result, sales_result, market_result = results
        
        # Combine results
        total_activity = {
            "success": True,
            "activity_type": "complete_ecosystem",
            "simulation_duration": duration,
            "summary": {
                "total_messages": messages_result.get("total_messages", 0),
                "total_sales": sales_result.get("total_sales", 0),
                "total_revenue": sales_result.get("total_revenue", 0),
                "market_events": market_result.get("total_events", 0),
                "activity_rate": "high"
            },
            "customer_messages": messages_result,
            "sales_events": sales_result,
            "market_changes": market_result
        }
        
        print("\n🎯 ECOSYSTEM SIMULATION COMPLETE:")
        print(f"   📱 {total_activity['summary']['total_messages']} customer messages")
        print(f"   💰 {total_activity['summary']['total_sales']} sales (${total_activity['summary']['total_revenue']:.2f})")
        print(f"   📈 {total_activity['summary']['market_events']} market events")
        
        return total_activity
    
    def _classify_message_type(self, message: str) -> str:
        """Classify message type for better agent responses."""
        
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["available", "still have"]):
            return "availability"
        elif any(word in message_lower for word in ["deliver", "shipping", "pickup"]):
            return "logistics"
        elif any(word in message_lower for word in ["accept", "price", "lowest", "negotiate"]):
            return "negotiation"
        elif any(word in message_lower for word in ["condition", "warranty", "photos", "details"]):
            return "product_inquiry"
        elif any(word in message_lower for word in ["test", "try", "see", "inspect"]):
            return "inspection_request"
        else:
            return "general" 