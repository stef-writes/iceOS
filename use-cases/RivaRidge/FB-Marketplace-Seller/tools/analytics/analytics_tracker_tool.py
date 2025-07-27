"""Analytics Tracker Tool - Tracks and analyzes marketplace selling performance."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from ice_core.base_tool import ToolBase


class AnalyticsTrackerTool(ToolBase):
    """Tracks and analyzes marketplace selling metrics and performance."""
    
    name: str = "analytics_tracker"
    description: str = "Analyzes marketplace performance metrics and generates insights"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Analyze marketplace performance data and generate insights."""
        listings_data = kwargs.get("listings_data", [])
        message_data = kwargs.get("message_data", [])
        start_time = kwargs.get("start_time")
        
        # Parse start time
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        else:
            start_time = datetime.now() - timedelta(hours=24)
            
        # Calculate key metrics
        listing_metrics = self._analyze_listings(listings_data)
        message_metrics = self._analyze_messages(message_data)
        conversion_metrics = self._calculate_conversions(listings_data, message_data)
        time_metrics = self._analyze_timing(listings_data, message_data, start_time)
        revenue_metrics = self._calculate_revenue(listings_data)
        
        # Generate insights and recommendations
        insights = self._generate_insights(
            listing_metrics, 
            message_metrics, 
            conversion_metrics,
            revenue_metrics
        )
        
        # Build comprehensive report
        return {
            "metrics_report": {
                "listings": listing_metrics,
                "messages": message_metrics,
                "conversions": conversion_metrics,
                "timing": time_metrics,
                "revenue": revenue_metrics
            },
            "performance_summary": {
                "total_listings": listing_metrics["total_count"],
                "total_revenue": revenue_metrics["total_revenue"],
                "conversion_rate": conversion_metrics["overall_rate"],
                "avg_response_time": message_metrics.get("avg_response_time_minutes", 0),
                "performance_score": self._calculate_performance_score(
                    listing_metrics, message_metrics, conversion_metrics
                )
            },
            "insights": insights,
            "report_timestamp": datetime.now().isoformat()
        }
    
    def _analyze_listings(self, listings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze listing performance metrics."""
        if not listings_data:
            return {
                "total_count": 0,
                "active_count": 0,
                "sold_count": 0,
                "avg_price": 0,
                "price_range": {"min": 0, "max": 0}
            }
            
        prices = [listing.get("price", 0) for listing in listings_data]
        statuses = [listing.get("status", "unknown") for listing in listings_data]
        
        return {
            "total_count": len(listings_data),
            "active_count": statuses.count("active"),
            "sold_count": statuses.count("sold"),
            "pending_count": statuses.count("pending"),
            "avg_price": statistics.mean(prices) if prices else 0,
            "median_price": statistics.median(prices) if prices else 0,
            "price_range": {
                "min": min(prices) if prices else 0,
                "max": max(prices) if prices else 0
            },
            "by_category": self._group_by_field(listings_data, "category"),
            "by_condition": self._group_by_field(listings_data, "condition")
        }
    
    def _analyze_messages(self, message_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze message and customer interaction metrics."""
        if not message_data:
            return {
                "total_messages": 0,
                "unique_conversations": 0,
                "avg_response_time_minutes": 0,
                "unanswered_count": 0
            }
            
        # Group messages by conversation/listing
        conversations = defaultdict(list)
        for msg in message_data:
            conv_id = msg.get("conversation_id") or msg.get("listing_id")
            if conv_id:
                conversations[conv_id].append(msg)
                
        # Calculate response times
        response_times = []
        unanswered = 0
        
        for conv_messages in conversations.values():
            # Sort by timestamp
            sorted_msgs = sorted(
                conv_messages, 
                key=lambda m: datetime.fromisoformat(m.get("timestamp", datetime.now().isoformat()))
            )
            
            # Look for response patterns
            for i in range(len(sorted_msgs) - 1):
                if sorted_msgs[i].get("is_buyer") and sorted_msgs[i+1].get("is_seller"):
                    # Calculate response time
                    t1 = datetime.fromisoformat(sorted_msgs[i]["timestamp"])
                    t2 = datetime.fromisoformat(sorted_msgs[i+1]["timestamp"])
                    response_times.append((t2 - t1).total_seconds() / 60)
                    
            # Check if last message needs response
            if sorted_msgs and sorted_msgs[-1].get("is_buyer"):
                unanswered += 1
                
        return {
            "total_messages": len(message_data),
            "unique_conversations": len(conversations),
            "avg_response_time_minutes": statistics.mean(response_times) if response_times else 0,
            "median_response_time_minutes": statistics.median(response_times) if response_times else 0,
            "unanswered_count": unanswered,
            "messages_per_conversation": statistics.mean(
                [len(msgs) for msgs in conversations.values()]
            ) if conversations else 0,
            "sentiment_breakdown": self._analyze_sentiment(message_data)
        }
    
    def _calculate_conversions(
        self, 
        listings_data: List[Dict[str, Any]], 
        message_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate conversion funnel metrics."""
        total_listings = len(listings_data)
        if total_listings == 0:
            return {
                "overall_rate": 0,
                "view_to_message_rate": 0,
                "message_to_sale_rate": 0
            }
            
        # Count listings with messages
        listings_with_messages = set()
        for msg in message_data:
            listing_id = msg.get("listing_id")
            if listing_id:
                listings_with_messages.add(listing_id)
                
        # Count sold listings
        sold_listings = [l for l in listings_data if l.get("status") == "sold"]
        
        # Calculate rates
        message_rate = len(listings_with_messages) / total_listings if total_listings > 0 else 0
        sale_rate = len(sold_listings) / len(listings_with_messages) if listings_with_messages else 0
        overall_rate = len(sold_listings) / total_listings if total_listings > 0 else 0
        
        return {
            "overall_rate": overall_rate,
            "view_to_message_rate": message_rate,
            "message_to_sale_rate": sale_rate,
            "funnel": {
                "total_listings": total_listings,
                "received_messages": len(listings_with_messages),
                "completed_sales": len(sold_listings)
            }
        }
    
    def _analyze_timing(
        self, 
        listings_data: List[Dict[str, Any]], 
        message_data: List[Dict[str, Any]],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Analyze timing patterns and trends."""
        # Time to first message
        times_to_first_message = []
        for listing in listings_data:
            listing_id = listing.get("listing_id")
            created_at = listing.get("created_at")
            
            if listing_id and created_at:
                # Find first message for this listing
                listing_messages = [
                    m for m in message_data 
                    if m.get("listing_id") == listing_id
                ]
                if listing_messages:
                    first_msg_time = min(
                        datetime.fromisoformat(m["timestamp"]) 
                        for m in listing_messages 
                        if "timestamp" in m
                    )
                    created_time = datetime.fromisoformat(created_at)
                    times_to_first_message.append(
                        (first_msg_time - created_time).total_seconds() / 3600
                    )
        
        # Time to sale
        times_to_sale = []
        for listing in listings_data:
            if listing.get("status") == "sold" and listing.get("sold_at"):
                created = datetime.fromisoformat(listing["created_at"])
                sold = datetime.fromisoformat(listing["sold_at"])
                times_to_sale.append((sold - created).total_seconds() / 3600)
                
        return {
            "avg_time_to_first_message_hours": (
                statistics.mean(times_to_first_message) if times_to_first_message else 0
            ),
            "avg_time_to_sale_hours": (
                statistics.mean(times_to_sale) if times_to_sale else 0
            ),
            "peak_message_hours": self._find_peak_hours(message_data),
            "days_active": (datetime.now() - start_time).days
        }
    
    def _calculate_revenue(self, listings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate revenue metrics."""
        sold_listings = [l for l in listings_data if l.get("status") == "sold"]
        revenues = [l.get("price", 0) for l in sold_listings]
        
        return {
            "total_revenue": sum(revenues),
            "avg_sale_price": statistics.mean(revenues) if revenues else 0,
            "revenue_by_category": self._sum_by_field(sold_listings, "category", "price"),
            "revenue_by_condition": self._sum_by_field(sold_listings, "condition", "price"),
            "daily_revenue": self._calculate_daily_revenue(sold_listings)
        }
    
    def _generate_insights(
        self,
        listing_metrics: Dict[str, Any],
        message_metrics: Dict[str, Any],
        conversion_metrics: Dict[str, Any],
        revenue_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable insights from metrics."""
        insights = []
        
        # Conversion insights
        if conversion_metrics["overall_rate"] < 0.1:
            insights.append({
                "type": "improvement",
                "area": "conversion",
                "message": "Low conversion rate (< 10%). Consider improving listing descriptions or pricing.",
                "priority": "high"
            })
            
        # Response time insights
        avg_response = message_metrics.get("avg_response_time_minutes", 0)
        if avg_response > 60:
            insights.append({
                "type": "improvement",
                "area": "response_time",
                "message": f"Average response time is {avg_response:.0f} minutes. Faster responses increase sales.",
                "priority": "high"
            })
            
        # Pricing insights
        if listing_metrics["avg_price"] > 0:
            price_variance = (
                (listing_metrics["price_range"]["max"] - listing_metrics["price_range"]["min"]) 
                / listing_metrics["avg_price"]
            )
            if price_variance > 2:
                insights.append({
                    "type": "observation",
                    "area": "pricing",
                    "message": "Wide price range detected. Consider segmenting strategy by price tier.",
                    "priority": "medium"
                })
                
        # Category performance
        by_category = revenue_metrics.get("revenue_by_category", {})
        if by_category:
            best_category = max(by_category.items(), key=lambda x: x[1])
            insights.append({
                "type": "success",
                "area": "category",
                "message": f"'{best_category[0]}' is your best performing category with ${best_category[1]:.2f} in sales.",
                "priority": "low"
            })
            
        # Unanswered messages
        if message_metrics.get("unanswered_count", 0) > 0:
            insights.append({
                "type": "action_required",
                "area": "messages",
                "message": f"{message_metrics['unanswered_count']} messages need responses.",
                "priority": "urgent"
            })
            
        return insights
    
    def _calculate_performance_score(
        self,
        listing_metrics: Dict[str, Any],
        message_metrics: Dict[str, Any],
        conversion_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall performance score (0-100)."""
        scores = []
        
        # Conversion score (40% weight)
        conversion_rate = conversion_metrics.get("overall_rate", 0)
        scores.append(min(conversion_rate * 200, 100) * 0.4)  # 50% conversion = 100 score
        
        # Response time score (30% weight)
        avg_response = message_metrics.get("avg_response_time_minutes", 120)
        response_score = max(0, 100 - (avg_response - 30))  # 30 min = 100, 130 min = 0
        scores.append(response_score * 0.3)
        
        # Activity score (30% weight)
        total_listings = listing_metrics.get("total_count", 0)
        activity_score = min(total_listings * 5, 100)  # 20 listings = 100
        scores.append(activity_score * 0.3)
        
        return sum(scores)
    
    def _group_by_field(
        self, 
        items: List[Dict[str, Any]], 
        field: str
    ) -> Dict[str, int]:
        """Group items by field value and count."""
        groups = defaultdict(int)
        for item in items:
            value = item.get(field, "unknown")
            groups[value] += 1
        return dict(groups)
    
    def _sum_by_field(
        self, 
        items: List[Dict[str, Any]], 
        group_field: str,
        sum_field: str
    ) -> Dict[str, float]:
        """Sum values by group field."""
        groups = defaultdict(float)
        for item in items:
            group = item.get(group_field, "unknown")
            value = item.get(sum_field, 0)
            groups[group] += value
        return dict(groups)
    
    def _analyze_sentiment(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """Simple sentiment analysis based on keywords."""
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        
        positive_keywords = ["thanks", "great", "perfect", "excellent", "love", "interested"]
        negative_keywords = ["bad", "poor", "damaged", "broken", "disappointed", "issue"]
        
        for msg in messages:
            content = msg.get("content", "").lower()
            
            has_positive = any(word in content for word in positive_keywords)
            has_negative = any(word in content for word in negative_keywords)
            
            if has_positive and not has_negative:
                sentiments["positive"] += 1
            elif has_negative and not has_positive:
                sentiments["negative"] += 1
            else:
                sentiments["neutral"] += 1
                
        return sentiments
    
    def _find_peak_hours(self, messages: List[Dict[str, Any]]) -> List[int]:
        """Find peak message hours."""
        hour_counts = defaultdict(int)
        
        for msg in messages:
            timestamp = msg.get("timestamp")
            if timestamp:
                hour = datetime.fromisoformat(timestamp).hour
                hour_counts[hour] += 1
                
        # Get top 3 hours
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, _ in sorted_hours[:3]]
    
    def _calculate_daily_revenue(self, sold_listings: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate revenue by day."""
        daily_revenue = defaultdict(float)
        
        for listing in sold_listings:
            sold_at = listing.get("sold_at")
            if sold_at:
                date = datetime.fromisoformat(sold_at).date().isoformat()
                daily_revenue[date] += listing.get("price", 0)
                
        return dict(daily_revenue)
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool inputs."""
        return {
            "type": "object",
            "properties": {
                "listings_data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "listing_id": {"type": "string"},
                            "status": {"type": "string"},
                            "price": {"type": "number"},
                            "created_at": {"type": "string"},
                            "sold_at": {"type": "string"},
                            "category": {"type": "string"},
                            "condition": {"type": "string"}
                        }
                    }
                },
                "message_data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "listing_id": {"type": "string"},
                            "conversation_id": {"type": "string"},
                            "timestamp": {"type": "string"},
                            "is_buyer": {"type": "boolean"},
                            "is_seller": {"type": "boolean"},
                            "content": {"type": "string"}
                        }
                    }
                },
                "start_time": {"type": "string", "format": "date-time"}
            },
            "required": ["listings_data"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool outputs."""
        return {
            "type": "object",
            "properties": {
                "metrics_report": {
                    "type": "object",
                    "properties": {
                        "listings": {"type": "object"},
                        "messages": {"type": "object"},
                        "conversions": {"type": "object"},
                        "timing": {"type": "object"},
                        "revenue": {"type": "object"}
                    }
                },
                "performance_summary": {
                    "type": "object",
                    "properties": {
                        "total_listings": {"type": "integer"},
                        "total_revenue": {"type": "number"},
                        "conversion_rate": {"type": "number"},
                        "avg_response_time": {"type": "number"},
                        "performance_score": {"type": "number"}
                    }
                },
                "insights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "area": {"type": "string"},
                            "message": {"type": "string"},
                            "priority": {"type": "string"}
                        }
                    }
                },
                "report_timestamp": {"type": "string", "format": "date-time"}
            },
            "required": ["metrics_report", "performance_summary", "insights", "report_timestamp"]
        } 