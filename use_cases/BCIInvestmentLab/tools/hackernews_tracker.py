"""
📰 HackerNewsTrackerTool - Tech Community Insights
=================================================

Highly reusable tool for tracking technology trends from Hacker News.
Perfect for any tech trend analysis use case.

## Reusability
✅ Any tech trend analysis use case
✅ Startup intelligence
✅ Developer sentiment tracking
✅ Technology adoption signals
✅ Innovation monitoring

## Features
- Real Hacker News API integration
- Technology trend detection
- Community sentiment analysis
- Startup and funding tracking
- Developer discussion analysis
"""

import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import Counter
import asyncio

from ice_sdk.tools.base import ToolBase
import structlog

logger = structlog.get_logger(__name__)


class HackerNewsTrackerTool(ToolBase):
    """Track technology trends and sentiment from Hacker News community.
    
    This tool monitors Hacker News for technology discussions, startup mentions,
    and community sentiment around specific topics or technologies.
    """
    
    name: str = "hackernews_tracker"
    description: str = "Track technology trends and sentiment from Hacker News community"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Execute Hacker News trend tracking.
        
        Args:
            query: Search terms or technology to track (required)
            time_window: Time window - 'today', 'week', 'month' (default: 'week')
            max_stories: Maximum number of stories to analyze (default: 100)
            include_comments: Whether to analyze comments (default: True)
            min_score: Minimum story score to include (default: 5)
            story_types: Types of stories to include - ['story', 'ask', 'show', 'job'] (default: ['story', 'ask', 'show'])
            
        Returns:
            Dict containing comprehensive Hacker News analysis
        """
        try:
            # Extract and validate parameters
            query = kwargs.get("query")
            if not query:
                raise ValueError("Query parameter is required")
            
            time_window = kwargs.get("time_window", "week")
            max_stories = kwargs.get("max_stories", 100)
            include_comments = kwargs.get("include_comments", True)
            min_score = kwargs.get("min_score", 5)
            story_types = kwargs.get("story_types", ["story", "ask", "show"])
            
            logger.info(f"Tracking HN trends for: '{query}' ({time_window} window)")
            
            # Import required libraries
            try:
                import requests
            except ImportError:
                return {
                    "error": "requests library not installed. Run: pip install requests",
                    "stories": [],
                    "analysis": {}
                }
            
            # Define time cutoff
            time_cutoff = self._get_time_cutoff(time_window)
            
            # Fetch stories from Hacker News
            stories = await self._fetch_hn_stories(query, max_stories, min_score, story_types, time_cutoff)
            
            if not stories:
                return {
                    "error": "No stories found matching criteria",
                    "stories": [],
                    "analysis": {}
                }
            
            # Fetch comments if requested
            comments_data = {}
            if include_comments:
                comments_data = await self._fetch_story_comments(stories[:20])  # Limit to top 20 stories
            
            # Analyze trends and sentiment
            trend_analysis = self._analyze_trends(stories, comments_data)
            
            # Extract key technologies and companies
            tech_analysis = self._analyze_technologies(stories, comments_data)
            
            # Analyze community sentiment
            sentiment_analysis = self._analyze_community_sentiment(stories, comments_data)
            
            # Generate insights
            insights = self._generate_insights(trend_analysis, tech_analysis, sentiment_analysis)
            
            return {
                "stories": stories,
                "trend_analysis": trend_analysis,
                "technology_analysis": tech_analysis,
                "sentiment_analysis": sentiment_analysis,
                "insights": insights,
                "metadata": {
                    "query": query,
                    "time_window": time_window,
                    "stories_analyzed": len(stories),
                    "comments_analyzed": sum(len(comments) for comments in comments_data.values()),
                    "min_score": min_score,
                    "story_types": story_types
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"HackerNewsTrackerTool execution failed: {e}")
            return {
                "error": str(e),
                "stories": [],
                "analysis": {},
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_time_cutoff(self, time_window: str) -> datetime:
        """Get time cutoff based on window."""
        now = datetime.now()
        if time_window == "today":
            return now - timedelta(days=1)
        elif time_window == "week":
            return now - timedelta(weeks=1)
        elif time_window == "month":
            return now - timedelta(days=30)
        else:
            return now - timedelta(weeks=1)  # Default to week
    
    async def _fetch_hn_stories(self, query: str, max_stories: int, min_score: int, 
                               story_types: List[str], time_cutoff: datetime) -> List[Dict[str, Any]]:
        """Fetch stories from Hacker News API."""
        import requests
        
        # Use HN Algolia API for searching
        base_url = "https://hn.algolia.com/api/v1/search"
        stories = []
        page = 0
        
        while len(stories) < max_stories and page < 10:  # Limit to 10 pages
            try:
                params = {
                    "query": query,
                    "tags": ",".join(f"story" if t == "story" else f"({t})" for t in story_types),
                    "hitsPerPage": 50,
                    "page": page
                }
                
                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if not data.get("hits"):
                    break
                
                for hit in data["hits"]:
                    # Parse timestamp
                    created_time = datetime.fromisoformat(hit["created_at"].replace("Z", "+00:00"))
                    
                    # Check time window and score
                    if created_time >= time_cutoff and hit.get("points", 0) >= min_score:
                        story = {
                            "id": hit["objectID"],
                            "title": hit["title"],
                            "url": hit["url"],
                            "score": hit.get("points", 0),
                            "num_comments": hit.get("num_comments", 0),
                            "author": hit["author"],
                            "created_at": hit["created_at"],
                            "story_type": hit.get("_tags", ["story"])[0] if hit.get("_tags") else "story",
                            "story_text": hit.get("story_text", ""),
                            "story_url": f"https://news.ycombinator.com/item?id={hit['objectID']}"
                        }
                        stories.append(story)
                
                page += 1
                await asyncio.sleep(0.1)  # Rate limiting
                
            except requests.RequestException as e:
                logger.warning(f"Error fetching HN stories page {page}: {e}")
                break
        
        # Sort by score and return top results
        stories.sort(key=lambda x: x["score"], reverse=True)
        return stories[:max_stories]
    
    async def _fetch_story_comments(self, stories: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch comments for top stories."""
        import requests
        
        comments_data = {}
        
        for story in stories:
            try:
                story_id = story["id"]
                url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                item_data = response.json()
                
                if item_data and "kids" in item_data:
                    comments = await self._fetch_comment_tree(item_data["kids"][:20])  # Top 20 comments
                    comments_data[story_id] = comments
                
                await asyncio.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Error fetching comments for story {story['id']}: {e}")
                continue
        
        return comments_data
    
    async def _fetch_comment_tree(self, comment_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch comment tree from HN API."""
        import requests
        
        comments = []
        
        for comment_id in comment_ids:
            try:
                url = f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                comment_data = response.json()
                
                if comment_data and comment_data.get("type") == "comment" and comment_data.get("text"):
                    comment = {
                        "id": comment_data["id"],
                        "text": comment_data["text"],
                        "author": comment_data.get("by", "unknown"),
                        "time": comment_data.get("time", 0),
                        "score": comment_data.get("score", 0)
                    }
                    comments.append(comment)
                
                await asyncio.sleep(0.05)  # Rate limiting
                
            except Exception:
                continue
        
        return comments
    
    def _analyze_trends(self, stories: List[Dict[str, Any]], comments_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze trending topics and patterns."""
        
        # Analyze story titles for trending terms
        all_titles = [story["title"] for story in stories]
        title_words = []
        
        for title in all_titles:
            # Clean and extract meaningful words
            words = re.findall(r'\b[A-Za-z]{3,}\b', title.lower())
            title_words.extend(words)
        
        # Filter out common words
        stopwords = {'the', 'and', 'for', 'with', 'you', 'are', 'can', 'new', 'how', 'why', 'what', 'this', 'that', 'from', 'your', 'app', 'web', 'use', 'now', 'get', 'all', 'has', 'was', 'not', 'but', 'his', 'her', 'out', 'one', 'two', 'who', 'oil', 'day', 'man', 'old', 'see', 'way', 'its', 'than', 'may', 'say', 'she', 'him', 'her', 'had', 'was', 'were', 'been', 'have', 'their', 'said', 'each', 'which', 'many', 'some', 'time', 'very', 'more', 'other', 'such', 'just', 'first', 'after', 'back', 'also', 'around', 'still', 'should', 'might', 'where', 'much', 'about'}
        
        filtered_words = [word for word in title_words if word not in stopwords and len(word) > 3]
        trending_terms = Counter(filtered_words).most_common(20)
        
        # Analyze story types distribution
        story_types = Counter(story["story_type"] for story in stories)
        
        # Analyze posting patterns over time
        posting_hours = []
        for story in stories:
            try:
                created_time = datetime.fromisoformat(story["created_at"].replace("Z", "+00:00"))
                posting_hours.append(created_time.hour)
            except:
                continue
        
        hour_distribution = Counter(posting_hours)
        
        # Analyze score patterns
        scores = [story["score"] for story in stories]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            "trending_terms": trending_terms,
            "story_types_distribution": dict(story_types),
            "posting_patterns": {
                "hour_distribution": dict(hour_distribution),
                "peak_hour": hour_distribution.most_common(1)[0][0] if hour_distribution else None
            },
            "engagement_metrics": {
                "avg_score": avg_score,
                "max_score": max(scores) if scores else 0,
                "total_comments": sum(story["num_comments"] for story in stories),
                "avg_comments": sum(story["num_comments"] for story in stories) / len(stories) if stories else 0
            }
        }
    
    def _analyze_technologies(self, stories: List[Dict[str, Any]], comments_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze mentioned technologies and companies."""
        
        # Define technology keywords
        technologies = {
            "ai": ["ai", "artificial intelligence", "machine learning", "ml", "neural", "llm", "gpt", "openai"],
            "blockchain": ["blockchain", "bitcoin", "ethereum", "crypto", "nft", "defi", "web3"],
            "cloud": ["aws", "azure", "gcp", "kubernetes", "docker", "serverless"],
            "frontend": ["react", "vue", "angular", "javascript", "typescript", "next.js"],
            "backend": ["python", "node.js", "golang", "rust", "java", "postgresql"],
            "mobile": ["ios", "android", "flutter", "react native", "swift", "kotlin"],
            "databases": ["postgresql", "mongodb", "redis", "elasticsearch", "sqlite"],
            "devops": ["kubernetes", "docker", "terraform", "ansible", "jenkins", "cicd"]
        }
        
        companies = ["google", "apple", "microsoft", "amazon", "meta", "facebook", "tesla", "nvidia", "openai", "anthropic", "spacex", "stripe", "airbnb", "uber", "spotify"]
        
        # Combine all text
        all_text = []
        for story in stories:
            all_text.append(story["title"])
            if story.get("story_text"):
                all_text.append(story["story_text"])
        
        for comments_list in comments_data.values():
            for comment in comments_list:
                all_text.append(comment["text"])
        
        combined_text = " ".join(all_text).lower()
        
        # Count technology mentions
        tech_mentions = {}
        for category, keywords in technologies.items():
            count = 0
            for keyword in keywords:
                count += combined_text.count(keyword.lower())
            if count > 0:
                tech_mentions[category] = count
        
        # Count company mentions
        company_mentions = {}
        for company in companies:
            count = combined_text.count(company.lower())
            if count > 0:
                company_mentions[company] = count
        
        return {
            "technology_mentions": tech_mentions,
            "company_mentions": company_mentions,
            "top_technologies": sorted(tech_mentions.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_companies": sorted(company_mentions.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def _analyze_community_sentiment(self, stories: List[Dict[str, Any]], comments_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze community sentiment around topics."""
        
        # Simple sentiment analysis using keyword counting
        positive_words = {
            'great', 'awesome', 'excellent', 'amazing', 'fantastic', 'brilliant', 'outstanding',
            'impressive', 'innovative', 'revolutionary', 'breakthrough', 'exciting', 'promising',
            'love', 'like', 'best', 'perfect', 'wonderful', 'successful', 'effective'
        }
        
        negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'disappointing', 'frustrating', 'broken',
            'useless', 'pointless', 'waste', 'failure', 'problem', 'issue', 'bug', 'annoying',
            'hate', 'dislike', 'worst', 'ridiculous', 'stupid', 'wrong', 'ineffective'
        }
        
        # Analyze story titles
        story_sentiments = []
        for story in stories:
            sentiment = self._calculate_text_sentiment(story["title"], positive_words, negative_words)
            story_sentiments.append(sentiment)
        
        # Analyze comments
        comment_sentiments = []
        for comments_list in comments_data.values():
            for comment in comments_list:
                sentiment = self._calculate_text_sentiment(comment["text"], positive_words, negative_words)
                comment_sentiments.append(sentiment)
        
        # Aggregate sentiment
        all_sentiments = story_sentiments + comment_sentiments
        
        if not all_sentiments:
            return {"error": "No sentiment data to analyze"}
        
        avg_sentiment = sum(all_sentiments) / len(all_sentiments)
        
        # Classify sentiment
        if avg_sentiment > 0.1:
            overall_sentiment = "positive"
        elif avg_sentiment < -0.1:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"
        
        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_score": avg_sentiment,
            "story_sentiment_avg": sum(story_sentiments) / len(story_sentiments) if story_sentiments else 0,
            "comment_sentiment_avg": sum(comment_sentiments) / len(comment_sentiments) if comment_sentiments else 0,
            "positive_ratio": len([s for s in all_sentiments if s > 0]) / len(all_sentiments),
            "negative_ratio": len([s for s in all_sentiments if s < 0]) / len(all_sentiments),
            "neutral_ratio": len([s for s in all_sentiments if s == 0]) / len(all_sentiments)
        }
    
    def _calculate_text_sentiment(self, text: str, positive_words: set, negative_words: set) -> float:
        """Calculate sentiment score for text."""
        if not text:
            return 0
        
        # Clean text
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        if not words:
            return 0
        
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        return (positive_count - negative_count) / len(words)
    
    def _generate_insights(self, trend_analysis: Dict[str, Any], tech_analysis: Dict[str, Any], 
                          sentiment_analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from the analysis."""
        insights = []
        
        # Trending technology insights
        if tech_analysis.get("top_technologies"):
            top_tech = tech_analysis["top_technologies"][0]
            insights.append(f"'{top_tech[0]}' is the most discussed technology category with {top_tech[1]} mentions")
        
        # Sentiment insights
        sentiment = sentiment_analysis.get("overall_sentiment", "neutral")
        if sentiment == "positive":
            insights.append("Community sentiment is positive, indicating optimism about current trends")
        elif sentiment == "negative":
            insights.append("Community sentiment is negative, suggesting concerns or skepticism")
        
        # Engagement insights
        engagement = trend_analysis.get("engagement_metrics", {})
        avg_score = engagement.get("avg_score", 0)
        if avg_score > 50:
            insights.append("High engagement levels suggest strong community interest in these topics")
        
        # Company insights
        if tech_analysis.get("top_companies"):
            top_company = tech_analysis["top_companies"][0]
            insights.append(f"'{top_company[0]}' is the most mentioned company with {top_company[1]} references")
        
        # Trending terms insights
        trending_terms = trend_analysis.get("trending_terms", [])
        if trending_terms:
            top_term = trending_terms[0]
            insights.append(f"'{top_term[0]}' is a trending term appearing in {top_term[1]} story titles")
        
        return insights

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return the input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms or technology to track"
                },
                "time_window": {
                    "type": "string",
                    "enum": ["today", "week", "month"],
                    "default": "week",
                    "description": "Time window for analysis"
                },
                "max_stories": {
                    "type": "integer",
                    "default": 100,
                    "minimum": 10,
                    "maximum": 500,
                    "description": "Maximum number of stories to analyze"
                },
                "include_comments": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to analyze comments"
                },
                "min_score": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "description": "Minimum story score to include"
                },
                "story_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["story", "ask", "show"],
                    "description": "Types of stories to include"
                }
            },
            "required": ["query"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return the output schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "stories": {
                    "type": "array",
                    "description": "List of analyzed stories"
                },
                "trend_analysis": {
                    "type": "object",
                    "description": "Trending topics and patterns"
                },
                "technology_analysis": {
                    "type": "object",
                    "description": "Technology and company mentions"
                },
                "sentiment_analysis": {
                    "type": "object",
                    "description": "Community sentiment analysis"
                },
                "insights": {
                    "type": "array",
                    "description": "Actionable insights"
                },
                "metadata": {
                    "type": "object",
                    "description": "Analysis parameters and statistics"
                },
                "timestamp": {
                    "type": "string",
                    "description": "When the analysis was performed"
                }
            }
        } 