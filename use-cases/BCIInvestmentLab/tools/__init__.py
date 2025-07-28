"""
🔧 BCI Investment Lab - Reusable Tools Ecosystem
===============================================

This package contains 9 tools, 8 of which are broadly reusable across many use cases.

## 🌟 Broadly Reusable Tools (8)

These tools are designed to be immediately reusable in other demos and projects:

### Academic & Research Tools
- `ArxivSearchTool` - Search academic papers from arXiv API
- `StatisticalAnalyzerTool` - Statistical analysis and trend detection
- `TechnologyReadinessTool` - Assess technology maturity levels

### Financial & Market Tools  
- `YahooFinanceFetcherTool` - Real-time stock data and financial metrics
- `CompanyResearchTool` - Company information and competitive analysis
- `TrendAnalyzerTool` - Time-series analysis and pattern detection

### Sentiment & Social Tools
- `NewsApiSentimentTool` - Financial sentiment from news articles (NewsAPI free tier)
- `HackerNewsTrackerTool` - Tech community trends from Hacker News

## 🧠 Domain-Specific Tools (1)

- `NeuralSimulatorTool` - Generate synthetic neural signals for BCI research

## 🚀 Quick Usage

```python
# Import reusable tools for your project
from use_cases.BCIInvestmentLab.tools import (
    ArxivSearchTool, StatisticalAnalyzerTool, YahooFinanceFetcherTool,
    NewsApiSentimentTool, HackerNewsTrackerTool, TechnologyReadinessTool,
    CompanyResearchTool, TrendAnalyzerTool
)

# Use in your workflow
papers = await ArxivSearchTool().execute(query="machine learning")
stats = await StatisticalAnalyzerTool().execute(data=papers)
stocks = await YahooFinanceFetcherTool().execute(symbols=["AAPL", "GOOGL"])
```

## 🏗️ Tool Registration

All tools are automatically registered in the iceOS unified registry for
immediate use in workflows, agents, and direct execution.
"""

# Import all tools for easy access
from .arxiv_search import ArxivSearchTool
from .statistical_analyzer import StatisticalAnalyzerTool  
from .yahoo_finance_fetcher import YahooFinanceFetcherTool
from .newsapi_sentiment import NewsApiSentimentTool
from .hackernews_tracker import HackerNewsTrackerTool
from .technology_readiness import TechnologyReadinessTool
from .company_research import CompanyResearchTool
from .trend_analyzer import TrendAnalyzerTool
from .neural_simulator import NeuralSimulatorTool

# Export for easy importing
__all__ = [
    # Broadly reusable tools (8)
    "ArxivSearchTool",
    "StatisticalAnalyzerTool", 
    "YahooFinanceFetcherTool",
    "NewsApiSentimentTool",
    "HackerNewsTrackerTool", 
    "TechnologyReadinessTool",
    "CompanyResearchTool",
    "TrendAnalyzerTool",
    
    # Domain-specific tools (1)
    "NeuralSimulatorTool",
] 