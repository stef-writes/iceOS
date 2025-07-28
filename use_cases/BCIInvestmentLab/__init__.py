"""BCI Investment Lab - Advanced iceOS Investment Analysis

Modular investment research system demonstrating sophisticated iceOS capabilities.
Uses MCP Blueprint API for clean architecture.
"""

# Import modular blueprints 
from .blueprints import (
    create_literature_analysis_blueprint,
    create_market_monitoring_blueprint,
    create_recursive_synthesis_blueprint
)

# Import components for registration
from .tools import *
from .agents import *

# Initialize BCI components for MCP API server
def initialize_tools():
    """Register BCI tools with the global registry."""
    from ice_core.models.enums import NodeType
    from ice_core.unified_registry import registry
    
    try:
        # Import all BCI tools
        from .tools import (
            ArxivSearchTool, YahooFinanceFetcherTool, NewsApiSentimentTool,
            CompanyResearchTool, TrendAnalyzerTool, StatisticalAnalyzerTool,
            TechnologyReadinessTool, NeuralSimulatorTool, HackerNewsTrackerTool
        )
        
        # Register tool instances
        tools = [
            ("arxiv_search", ArxivSearchTool()),
            ("yahoo_finance_fetcher", YahooFinanceFetcherTool()),
            ("newsapi_sentiment", NewsApiSentimentTool()),
            ("company_research", CompanyResearchTool()),
            ("trend_analyzer", TrendAnalyzerTool()),
            ("statistical_analyzer", StatisticalAnalyzerTool()),
            ("technology_readiness", TechnologyReadinessTool()),
            ("neural_simulator", NeuralSimulatorTool()),
            ("hackernews_tracker", HackerNewsTrackerTool())
        ]
        
        for name, tool in tools:
            registry.register_instance(NodeType.TOOL, name, tool)
        
        print(f"✅ BCI tools registered: {len(tools)} tools")
        return True
    except Exception as e:
        print(f"❌ BCI tool registration failed: {e}")
        return False

def initialize_agents():
    """Register BCI agents with the global registry.""" 
    from ice_core.unified_registry import global_agent_registry
    
    try:
        agents = [
            ("neuroscience_researcher", "use_cases.BCIInvestmentLab.agents.neuroscience_researcher"),
            ("market_intelligence", "use_cases.BCIInvestmentLab.agents.market_intelligence"),
            ("investment_coordinator", "use_cases.BCIInvestmentLab.agents.investment_coordinator")
        ]
        
        for name, path in agents:
            global_agent_registry.register_agent(name, path)
        
        print(f"✅ BCI agents registered: {len(agents)} agents")
        return True
    except Exception as e:
        print(f"❌ BCI agent registration failed: {e}")
        return False

def initialize_all(context: str = "standalone") -> bool:
    """Initialize all BCI Investment Lab components."""
    print(f"🧠 Initializing BCI Investment Lab (context: {context})...")
    
    tools_ok = initialize_tools()
    agents_ok = initialize_agents()
    
    if tools_ok and agents_ok:
        print("✅ BCI Investment Lab initialization complete")
        return True
    else:
        print("❌ BCI Investment Lab initialization failed")
        return False

# Export registry information
AGENT_REGISTRY = [
    ("neuroscience_researcher", "use_cases.BCIInvestmentLab.agents.neuroscience_researcher"),
    ("market_intelligence", "use_cases.BCIInvestmentLab.agents.market_intelligence"), 
    ("investment_coordinator", "use_cases.BCIInvestmentLab.agents.investment_coordinator")
]

__all__ = [
    "create_literature_analysis_blueprint",
    "create_market_monitoring_blueprint",
    "create_recursive_synthesis_blueprint",
    "initialize_all",
    "AGENT_REGISTRY"
] 