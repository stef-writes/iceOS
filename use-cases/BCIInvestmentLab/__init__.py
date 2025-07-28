"""
🧠💰 BCI Investment Intelligence Engine
======================================

AI Research Assistant that reads cutting-edge neuroscience papers, identifies 
commercial opportunities, tracks relevant companies, and predicts optimal 
investment timing windows.

This use case showcases EVERY advanced iceOS capability:
- ✅ All 9 node types (Tool, LLM, Agent, Code, Condition, Loop, Parallel, Recursive, Workflow)
- ✅ 4-tier memory system (Working, Episodic, Semantic, Procedural)
- ✅ Real API integrations (arXiv, Yahoo Finance, Reddit, HackerNews)
- ✅ WASM security and resource monitoring
- ✅ Agent-to-agent communication
- ✅ Recursive workflows with convergence
- ✅ Enterprise-grade observability

## Quick Start

```python
from use_cases.BCIInvestmentLab import run_bci_intelligence_demo

# Run complete BCI investment analysis
result = await run_bci_intelligence_demo(
    research_topic="non-invasive brain computer interfaces",
    companies=["META", "GOOGL", "AAPL", "NVDA"],
    confidence_threshold=0.85
)

print(f"Investment Recommendation: {result['investment_thesis']}")
print(f"Technology Readiness: {result['tech_readiness_score']}")
print(f"Market Opportunity: {result['market_timing']}")
```

## Architecture

### Research Intelligence (Phase 1)
- **arXiv Search** → **Paper Analysis Loop** → **Statistical Analysis**
- **Neuroscience Agent** (All 4 memory types) synthesizes research trends

### Market Intelligence (Phase 2)  
- **Parallel Execution**: Stock data + Reddit sentiment + HN discussions
- **Market Agent** (Economic memory) tracks companies and trends

### Recursive Synthesis (Phase 3)
- **Recursive Agent**: Scientist ↔ Economist iterative refinement
- **Convergence**: When investment confidence > 90%

### Report Generation (Phase 4)
- **LLM Nodes**: Literature synthesis + Investment thesis
- **Code Node**: Neural signal simulation for technical validation

## Reusable Components

This project builds 8+ tools that are immediately reusable:

### 🔧 Broadly Reusable Tools
- `arxiv_search.py` - Any academic research use case
- `statistical_analyzer.py` - Any data analysis use case  
- `yahoo_finance_fetcher.py` - Any financial analysis use case
- `reddit_sentiment.py` - Any sentiment analysis use case
- `hackernews_tracker.py` - Any tech trend analysis use case
- `technology_readiness.py` - Any emerging tech assessment
- `company_research.py` - Any competitive analysis use case
- `trend_analyzer.py` - Any time-series analysis use case

### 🧠 Domain-Specific
- `neural_simulator.py` - Code node capabilities for neural signal processing

## Enterprise Features

- **Multi-Agent Coordination**: Research ↔ Market ↔ Investment agents
- **Memory Persistence**: Long-term knowledge accumulation
- **Real-time Monitoring**: Live execution tracking via events
- **Security Isolation**: WASM sandboxing for code execution
- **Resource Management**: CPU, memory, and time limits
- **Error Recovery**: Graceful failure handling
- **Observability**: Complete metrics and tracing

"""

from .registry import register_bci_components
# Import workflows for use  
from .workflows import (
    create_literature_analysis_workflow,
    create_market_monitoring_workflow,
    create_recursive_synthesis_workflow
)

__all__ = [
    "register_bci_components",
    # Workflow creators for use
    "create_literature_analysis_workflow",
    "create_market_monitoring_workflow",
    "create_recursive_synthesis_workflow"
] 