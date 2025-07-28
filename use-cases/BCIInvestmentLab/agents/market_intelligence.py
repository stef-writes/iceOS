"""
📈 Market Intelligence Agent
===========================

Expert agent for financial market analysis and investment intelligence.

This agent specializes in:
- Market trend analysis and pattern recognition  
- Company research and competitive analysis
- Investment signal detection
- Sentiment analysis from multiple sources
- Financial data interpretation

Memory Usage:
- **Episodic Memory**: Market events, trading sessions, economic announcements
- **Semantic Memory**: Financial facts, company information, market relationships
- **Procedural Memory**: Analysis strategies, successful trading patterns, market methodologies
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import Field

from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig
from ice_orchestrator.memory import UnifiedMemoryConfig, MemoryConfig
from ice_core.models.llm import LLMConfig
from ice_core.models.node_models import ToolConfig

# Import available tools
from use_cases.BCIInvestmentLab.tools import (
    YahooFinanceFetcherTool,
    NewsApiSentimentTool,
    CompanyResearchTool,
    TrendAnalyzerTool,
    HackerNewsTrackerTool
)


class MarketIntelligenceConfig(MemoryAgentConfig):
    """Configuration for the Market Intelligence Agent."""
    
    type: str = "agent"
    package: str = "use_cases.BCIInvestmentLab.agents.market_intelligence"
    agent_attr: str = "MarketIntelligenceAgent"
    
    # Economic-focused memory configuration
    memory_config: UnifiedMemoryConfig = Field(
        default_factory=lambda: UnifiedMemoryConfig(
            enable_working=False,  # Market agent focuses on persistent memory
            enable_episodic=True,   # Track market events and sessions
            enable_semantic=True,   # Store financial facts and relationships
            enable_procedural=True, # Learn successful analysis patterns
            episodic_config=MemoryConfig(backend="redis", ttl_seconds=86400 * 90),  # 90 days of market history
            semantic_config=MemoryConfig(backend="sqlite"),  # Persistent market knowledge
            procedural_config=MemoryConfig(backend="file")   # Market analysis methods
        )
    )
    
    # Market-focused LLM configuration
    llm_config: LLMConfig = Field(
        default_factory=lambda: LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            temperature=0.2,  # Very low for precise financial analysis
            max_tokens=3000
        )
    )
    
    # Market analysis tools
    tools: List[ToolConfig] = Field(
        default_factory=lambda: [
            ToolConfig(name="yahoo_finance", package="use_cases.BCIInvestmentLab.tools.yahoo_finance_fetcher"),
            ToolConfig(name="newsapi_sentiment", package="use_cases.BCIInvestmentLab.tools.newsapi_sentiment"),
            ToolConfig(name="company_research", package="use_cases.BCIInvestmentLab.tools.company_research"),
            ToolConfig(name="trend_analyzer", package="use_cases.BCIInvestmentLab.tools.trend_analyzer"),
            ToolConfig(name="hackernews_tracker", package="use_cases.BCIInvestmentLab.tools.hackernews_tracker")
        ]
    )


class MarketIntelligenceAgent(MemoryAgent):
    """Expert market intelligence agent with economic memory focus.
    
    This agent provides sophisticated market analysis through:
    - Real-time financial data monitoring
    - Multi-source sentiment analysis  
    - Company and competitive intelligence
    - Market pattern recognition
    - Investment signal generation
    
    Example usage:
    ```python
    agent = MarketIntelligenceAgent()
    result = await agent.execute({
        "analysis_type": "market_sentiment",
        "companies": ["AAPL", "GOOGL", "MSFT"],
        "time_range": "30_days",
        "focus": "AI_and_technology"
    })
    ```
    """
    
    config: MarketIntelligenceConfig
    
    def __init__(self, config: Optional[MarketIntelligenceConfig] = None):
        """Initialize the market intelligence agent.
        
        Args:
            config: Agent configuration, uses defaults if None
        """
        if config is None:
            config = MarketIntelligenceConfig()
        super().__init__(config)
        
        # Market focus areas
        self.market_sectors = [
            "technology",
            "healthcare",
            "biotech",
            "artificial_intelligence",
            "neurotechnology",
            "medical_devices",
            "venture_capital",
            "growth_stocks",
            "emerging_markets"
        ]
        
        # Key BCI-related companies to track
        self.bci_companies = [
            "NURO",  # Neuralink (when public)
            "GTBP",  # GT Biopharma
            "CBDD",  # CBD Denver
            "BNRG",  # Brenmiller Energy
            # Add more as they become available
        ]
        
    async def _execute_with_memory(self, enhanced_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute market analysis with memory-enhanced context.
        
        Args:
            enhanced_inputs: Inputs enhanced with memory context
            
        Returns:
            Market intelligence analysis results
        """
        analysis_type = enhanced_inputs.get("analysis_type", "comprehensive")
        companies = enhanced_inputs.get("companies", self.bci_companies)
        time_range = enhanced_inputs.get("time_range", "30_days")
        focus = enhanced_inputs.get("focus", "bci_technology")
        
        # Load market context from memory
        context = await self._load_market_context(companies, focus)
        
        # Perform financial data analysis
        financial_data = await self._analyze_financial_data(companies, time_range)
        
        # Analyze market sentiment
        sentiment_analysis = await self._analyze_market_sentiment(companies, focus)
        
        # Research company fundamentals
        company_analysis = await self._research_companies(companies)
        
        # Detect market trends and patterns
        trend_analysis = await self._analyze_market_trends(financial_data, sentiment_analysis)
        
        # Generate investment signals
        signals = await self._generate_investment_signals(
            financial_data, sentiment_analysis, company_analysis, trend_analysis, context
        )
        
        # Store market session in memory
        await self._store_market_session(
            analysis_type, companies, financial_data, sentiment_analysis, signals
        )
        
        return {
            "status": "success",
            "analysis_type": analysis_type,
            "companies_analyzed": companies,
            "time_range": time_range,
            "financial_summary": self._summarize_financial_data(financial_data),
            "sentiment_summary": self._summarize_sentiment(sentiment_analysis),
            "company_insights": self._extract_company_insights(company_analysis),
            "market_trends": trend_analysis.get("trends", []),
            "investment_signals": signals,
            "risk_assessment": await self._assess_market_risks(financial_data, trend_analysis),
            "recommendations": await self._generate_market_recommendations(signals, context),
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "data_sources": ["yahoo_finance", "newsapi", "company_research", "hackernews"],
                "market_sectors": self._identify_sectors(companies),
                "confidence_score": self._calculate_confidence_score(financial_data, sentiment_analysis)
            }
        }
        
    async def _load_market_context(self, companies: List[str], focus: str) -> Dict[str, Any]:
        """Load relevant market context from memory.
        
        Args:
            companies: Companies to analyze
            focus: Analysis focus area
            
        Returns:
            Market context from memory
        """
        context = {}
        
        if self.memory:
            # Load historical market events
            if self.memory.episodic:
                market_events = await self.memory.search_memory(
                    f"market events {focus}",
                    memory_types=["episodic"],
                    limit=15
                )
                context["historical_events"] = market_events
                
                # Load past analysis for these companies
                for company in companies[:3]:  # Limit to avoid too many queries
                    company_history = await self.memory.search_memory(
                        f"company analysis {company}",
                        memory_types=["episodic"],
                        limit=5
                    )
                    if company_history:
                        context[f"{company}_history"] = company_history
                        
            # Load market facts and relationships
            if self.memory.semantic:
                market_facts = await self.memory.search_memory(
                    f"{focus} market analysis",
                    memory_types=["semantic"],
                    limit=25
                )
                context["market_knowledge"] = market_facts
                
            # Load successful analysis procedures
            if self.memory.procedural:
                analysis_methods = await self.memory.search_memory(
                    f"successful market analysis {focus}",
                    memory_types=["procedural"],
                    limit=10
                )
                context["proven_methods"] = analysis_methods
                
        return context
        
    async def _analyze_financial_data(self, companies: List[str], time_range: str) -> Dict[str, Any]:
        """Analyze financial data for specified companies.
        
        Args:
            companies: List of company symbols
            time_range: Time range for analysis
            
        Returns:
            Financial data analysis results
        """
        try:
            yahoo_tool = YahooFinanceFetcherTool()
            
            # Map time range to periods
            period_map = {
                "7_days": "7d",
                "30_days": "1mo", 
                "90_days": "3mo",
                "1_year": "1y",
                "all": "max"
            }
            period = period_map.get(time_range, "1mo")
            
            financial_results = {}
            for company in companies:
                try:
                    result = await yahoo_tool.execute({
                        "symbols": [company],
                        "period": period,
                        "include_financials": True,
                        "include_analysis": True
                    })
                    
                    if result.get("success"):
                        financial_results[company] = result.get("data", {})
                        
                except Exception as e:
                    await self._log_error(f"financial_analysis_{company}", str(e))
                    
            return financial_results
            
        except Exception as e:
            await self._log_error("financial_analysis", str(e))
            return {}
            
    async def _analyze_market_sentiment(self, companies: List[str], focus: str) -> Dict[str, Any]:
        """Analyze market sentiment from multiple sources.
        
        Args:
            companies: Companies to analyze sentiment for
            focus: Focus area for sentiment analysis
            
        Returns:
            Sentiment analysis results
        """
        sentiment_results = {}
        
        try:
            # NewsAPI sentiment analysis (free tier)
            newsapi_tool = NewsApiSentimentTool()
            for company in companies[:3]:  # Limit to stay within free tier
                try:
                    newsapi_result = await newsapi_tool.execute({
                        "query": f"{company} {focus} financial news",
                        "companies": [company],
                        "timeframe": "7d", 
                        "sentiment_focus": "financial",
                        "max_articles": 20  # Conservative for free tier
                    })
                    sentiment_results[f"{company}_newsapi"] = newsapi_result
                except Exception as e:
                    await self._log_error(f"newsapi_sentiment_{company}", str(e))
                    
            # HackerNews tech sentiment
            hn_tool = HackerNewsTrackerTool()
            try:
                hn_result = await hn_tool.execute({
                    "keywords": [focus, "BCI", "neurotechnology"],
                    "timeframe": "30d",
                    "min_score": 10
                })
                sentiment_results["hackernews_tech"] = hn_result
            except Exception as e:
                await self._log_error("hackernews_sentiment", str(e))
                
        except Exception as e:
            await self._log_error("sentiment_analysis", str(e))
            
        return sentiment_results
        
    async def _research_companies(self, companies: List[str]) -> Dict[str, Any]:
        """Research company fundamentals and competitive position.
        
        Args:
            companies: Companies to research
            
        Returns:
            Company research results
        """
        research_results = {}
        
        try:
            research_tool = CompanyResearchTool()
            
            for company in companies:
                try:
                    result = await research_tool.execute({
                        "company_symbol": company,
                        "research_depth": "comprehensive",
                        "include_competitors": True,
                        "focus_areas": ["technology", "financials", "market_position"]
                    })
                    research_results[company] = result
                except Exception as e:
                    await self._log_error(f"company_research_{company}", str(e))
                    
        except Exception as e:
            await self._log_error("company_research", str(e))
            
        return research_results
        
    async def _analyze_market_trends(
        self, 
        financial_data: Dict[str, Any], 
        sentiment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze market trends and patterns.
        
        Args:
            financial_data: Financial analysis results
            sentiment_data: Sentiment analysis results
            
        Returns:
            Trend analysis results
        """
        try:
            trend_tool = TrendAnalyzerTool()
            
            # Combine financial and sentiment data for trend analysis
            combined_data = {
                "financial_metrics": financial_data,
                "sentiment_metrics": sentiment_data,
                "analysis_type": "market_trends",
                "focus_sectors": self.market_sectors
            }
            
            result = await trend_tool.execute(combined_data)
            return result.get("analysis", {})
            
        except Exception as e:
            await self._log_error("trend_analysis", str(e))
            return {"trends": [], "patterns": []}
            
    async def _generate_investment_signals(
        self,
        financial_data: Dict[str, Any],
        sentiment_data: Dict[str, Any], 
        company_data: Dict[str, Any],
        trend_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate investment signals from all analysis.
        
        Args:
            financial_data: Financial analysis
            sentiment_data: Sentiment analysis
            company_data: Company research
            trend_data: Trend analysis
            context: Memory context
            
        Returns:
            List of investment signals
        """
        signals = []
        
        # Analyze each company for signals
        for company in financial_data.keys():
            company_financial = financial_data.get(company, {})
            company_research = company_data.get(company, {})
            
            signal = self._evaluate_company_signal(
                company, company_financial, company_research, sentiment_data, trend_data, context
            )
            
            if signal:
                signals.append(signal)
                
        # Generate market-wide signals
        market_signal = self._evaluate_market_signal(trend_data, sentiment_data, context)
        if market_signal:
            signals.append(market_signal)
            
        return signals
        
    def _evaluate_company_signal(
        self,
        company: str,
        financial: Dict[str, Any],
        research: Dict[str, Any],
        sentiment: Dict[str, Any],
        trends: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate investment signal for a specific company.
        
        Args:
            company: Company symbol
            financial: Financial data
            research: Research data
            sentiment: Sentiment data
            trends: Trend data
            context: Memory context
            
        Returns:
            Investment signal if significant, None otherwise
        """
        signal_strength = 0
        signal_factors = []
        
        # Analyze financial metrics
        if financial.get("price_change_percent", 0) > 5:
            signal_strength += 1
            signal_factors.append("positive_price_momentum")
        elif financial.get("price_change_percent", 0) < -5:
            signal_strength -= 1
            signal_factors.append("negative_price_momentum")
            
        # Analyze sentiment
        company_sentiment = sentiment.get(f"{company}_newsapi", {})
        if company_sentiment.get("sentiment_score", 0) > 0.6:
            signal_strength += 1
            signal_factors.append("positive_sentiment")
        elif company_sentiment.get("sentiment_score", 0) < 0.4:
            signal_strength -= 1
            signal_factors.append("negative_sentiment")
            
        # Check for significant news or events
        if research.get("recent_news_impact", 0) > 0.7:
            signal_strength += 2
            signal_factors.append("major_news_impact")
            
        # Minimum threshold for signal generation
        if abs(signal_strength) >= 2:
            return {
                "company": company,
                "signal_type": "buy" if signal_strength > 0 else "sell",
                "strength": abs(signal_strength),
                "confidence": min(abs(signal_strength) / 4.0, 1.0),
                "factors": signal_factors,
                "timestamp": datetime.now().isoformat()
            }
            
        return None
        
    def _evaluate_market_signal(
        self,
        trends: Dict[str, Any],
        sentiment: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate market-wide investment signal.
        
        Args:
            trends: Trend analysis
            sentiment: Sentiment analysis
            context: Memory context
            
        Returns:
            Market signal if significant, None otherwise
        """
        # Simple market signal based on overall trends
        market_trends = trends.get("trends", [])
        if len(market_trends) > 3:  # Strong trend indication
            trend_sentiment = sum(1 for trend in market_trends if "positive" in str(trend).lower())
            
            if trend_sentiment > len(market_trends) * 0.7:
                return {
                    "signal_type": "market_bullish",
                    "strength": 3,
                    "confidence": 0.7,
                    "factors": ["multiple_positive_trends", "sector_momentum"],
                    "timestamp": datetime.now().isoformat()
                }
                
        return None
        
    async def _store_market_session(
        self,
        analysis_type: str,
        companies: List[str],
        financial_data: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        signals: List[Dict[str, Any]]
    ) -> None:
        """Store market analysis session in memory.
        
        Args:
            analysis_type: Type of analysis performed
            companies: Companies analyzed
            financial_data: Financial results
            sentiment_data: Sentiment results
            signals: Generated signals
        """
        if not self.memory:
            return
            
        timestamp = datetime.now().isoformat()
        
        # Store in episodic memory
        if self.memory.episodic:
            await self.memory.episodic.store(
                f"episode:market_session:{timestamp}",
                {
                    "analysis_type": analysis_type,
                    "companies": companies,
                    "signals_generated": len(signals),
                    "strong_signals": [s for s in signals if s.get("strength", 0) >= 3],
                    "timestamp": timestamp
                },
                metadata={"type": "market_analysis", "companies": companies}
            )
            
        # Store significant findings in semantic memory
        if self.memory.semantic:
            for signal in signals:
                if signal.get("strength", 0) >= 3:  # Only store strong signals
                    await self.memory.semantic.store(
                        f"fact:strong_signal:{signal['company']}:{hash(str(signal))}",
                        signal,
                        metadata={"type": "investment_signal", "timestamp": timestamp}
                    )
                    
        # Store successful analysis procedures
        if self.memory.procedural:
            if len(signals) > 0:  # Successful if generated signals
                await self.memory.procedural.store(
                    f"procedure:successful_analysis:{hash(analysis_type)}",
                    {
                        "analysis_type": analysis_type,
                        "success_metrics": {"signals_generated": len(signals)},
                        "companies_analyzed": len(companies),
                        "timestamp": timestamp
                    },
                    metadata={"type": "successful_market_analysis"}
                )
                
    def _summarize_financial_data(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize financial data for output.
        
        Args:
            financial_data: Raw financial data
            
        Returns:
            Financial data summary
        """
        if not financial_data:
            return {"status": "no_data"}
            
        summary = {
            "companies_analyzed": len(financial_data),
            "average_performance": 0,
            "top_performers": [],
            "underperformers": []
        }
        
        performances = []
        for company, data in financial_data.items():
            perf = data.get("price_change_percent", 0)
            performances.append((company, perf))
            
        if performances:
            performances.sort(key=lambda x: x[1], reverse=True)
            summary["average_performance"] = sum(p[1] for p in performances) / len(performances)
            summary["top_performers"] = performances[:2]
            summary["underperformers"] = performances[-2:]
            
        return summary
        
    def _summarize_sentiment(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize sentiment analysis results.
        
        Args:
            sentiment_data: Raw sentiment data
            
        Returns:
            Sentiment summary
        """
        if not sentiment_data:
            return {"status": "no_data"}
            
        sentiment_scores = []
        for source, data in sentiment_data.items():
            if isinstance(data, dict) and "sentiment_score" in data:
                sentiment_scores.append(data["sentiment_score"])
                
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            return {
                "overall_sentiment": "positive" if avg_sentiment > 0.6 else "negative" if avg_sentiment < 0.4 else "neutral",
                "sentiment_score": avg_sentiment,
                "sources_analyzed": len(sentiment_scores)
            }
            
        return {"status": "insufficient_data"}
        
    def _extract_company_insights(self, company_data: Dict[str, Any]) -> List[str]:
        """Extract key insights from company research.
        
        Args:
            company_data: Company research data
            
        Returns:
            List of key insights
        """
        insights = []
        
        for company, data in company_data.items():
            if isinstance(data, dict):
                # Extract key metrics or findings
                if data.get("competitive_advantage"):
                    insights.append(f"{company}: Strong competitive position")
                if data.get("growth_potential", 0) > 0.7:
                    insights.append(f"{company}: High growth potential identified")
                if data.get("risk_factors"):
                    insights.append(f"{company}: Notable risk factors present")
                    
        return insights[:5]  # Limit to top insights
        
    def _identify_sectors(self, companies: List[str]) -> List[str]:
        """Identify market sectors for analyzed companies.
        
        Args:
            companies: List of company symbols
            
        Returns:
            List of relevant sectors
        """
        # Simple sector mapping - could be enhanced with real sector data
        bci_related_sectors = ["technology", "healthcare", "biotech", "neurotechnology"]
        return bci_related_sectors
        
    def _calculate_confidence_score(
        self, 
        financial_data: Dict[str, Any], 
        sentiment_data: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence score for analysis.
        
        Args:
            financial_data: Financial analysis data
            sentiment_data: Sentiment analysis data
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        score = 0.5  # Base score
        
        # Increase confidence with more data sources
        if financial_data:
            score += 0.2
        if sentiment_data:
            score += 0.2
            
        # Adjust based on data quality
        if len(financial_data) > 3:
            score += 0.1
            
        return min(score, 1.0)
        
    async def _assess_market_risks(
        self, 
        financial_data: Dict[str, Any], 
        trend_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess market risks from analysis.
        
        Args:
            financial_data: Financial data
            trend_data: Trend analysis
            
        Returns:
            Risk assessment
        """
        risks = {
            "overall_risk": "medium",
            "risk_factors": [],
            "volatility_indicators": []
        }
        
        # Analyze volatility from financial data
        high_volatility_count = 0
        for company, data in financial_data.items():
            volatility = data.get("volatility", 0)
            if volatility > 0.3:  # High volatility threshold
                high_volatility_count += 1
                risks["volatility_indicators"].append(f"{company}: High volatility")
                
        if high_volatility_count > len(financial_data) * 0.5:
            risks["overall_risk"] = "high"
            risks["risk_factors"].append("High market volatility detected")
            
        # Check trend consistency
        trends = trend_data.get("trends", [])
        conflicting_trends = sum(1 for trend in trends if "declining" in str(trend).lower())
        if conflicting_trends > len(trends) * 0.4:
            risks["risk_factors"].append("Conflicting market trends detected")
            
        return risks
        
    async def _generate_market_recommendations(
        self, 
        signals: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate market recommendations from analysis.
        
        Args:
            signals: Investment signals
            context: Memory context
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        strong_buy_signals = [s for s in signals if s.get("signal_type") == "buy" and s.get("strength", 0) >= 3]
        strong_sell_signals = [s for s in signals if s.get("signal_type") == "sell" and s.get("strength", 0) >= 3]
        
        if strong_buy_signals:
            companies = [s["company"] for s in strong_buy_signals]
            recommendations.append(f"Consider buy positions in: {', '.join(companies)}")
            
        if strong_sell_signals:
            companies = [s["company"] for s in strong_sell_signals]
            recommendations.append(f"Consider reducing exposure to: {', '.join(companies)}")
            
        # Market timing recommendations
        market_signals = [s for s in signals if s.get("signal_type", "").startswith("market_")]
        if market_signals:
            recommendations.append("Market-wide opportunities detected")
            
        # Risk management
        if len(signals) == 0:
            recommendations.append("Hold current positions - insufficient signal strength")
            
        return recommendations
        
    async def _log_error(self, operation: str, error: str) -> None:
        """Log errors for debugging.
        
        Args:
            operation: Operation that failed
            error: Error message
        """
        # For market agent, we don't use working memory, so log elsewhere
        if self.memory and self.memory.episodic:
            await self.memory.episodic.store(
                f"episode:error:{operation}:{datetime.now().isoformat()}",
                {
                    "operation": operation,
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                },
                metadata={"type": "error_log"}
            )


# Export for registration
__all__ = ["MarketIntelligenceAgent", "MarketIntelligenceConfig"] 