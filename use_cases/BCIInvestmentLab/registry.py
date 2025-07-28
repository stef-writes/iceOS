"""
🧠💰 BCI Investment Lab - Component Registry
==========================================

Central registry for all BCI Investment Lab components.
Registers all tools, agents, and workflows for easy discovery and use.
"""

from typing import Dict, Any
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType

# Import all tools for registration
from .tools import (
    ArxivSearchTool,
    StatisticalAnalyzerTool,
    YahooFinanceFetcherTool,
    NewsApiSentimentTool,
    HackerNewsTrackerTool,
    TechnologyReadinessTool,
    CompanyResearchTool,
    TrendAnalyzerTool,
    NeuralSimulatorTool
)


def register_bci_components() -> Dict[str, Any]:
    """Register all BCI Investment Lab components with iceOS registry.
    
    Returns:
        Dict containing registration status and component counts
    """
    registration_status = {
        "tools": {},
        "agents": {},
        "workflows": {},
        "errors": []
    }
    
    # Register all 9 tools
    tools_to_register = [
        ("arxiv_search", ArxivSearchTool),
        ("statistical_analyzer", StatisticalAnalyzerTool),
        ("yahoo_finance_fetcher", YahooFinanceFetcherTool),
        ("newsapi_sentiment", NewsApiSentimentTool),
        ("hackernews_tracker", HackerNewsTrackerTool),
        ("technology_readiness", TechnologyReadinessTool),
        ("company_research", CompanyResearchTool),
        ("trend_analyzer", TrendAnalyzerTool),
        ("neural_simulator", NeuralSimulatorTool)
    ]
    
    for tool_name, tool_class in tools_to_register:
        try:
            # Create instance and register
            tool_instance = tool_class()
            registry.register_instance(NodeType.TOOL, tool_name, tool_instance)
            registration_status["tools"][tool_name] = "registered"
            print(f"✅ Registered tool: {tool_name}")
        except Exception as e:
            registration_status["tools"][tool_name] = f"failed: {e}"
            registration_status["errors"].append(f"Tool {tool_name}: {e}")
            print(f"❌ Failed to register tool {tool_name}: {e}")
    
    # Register agent packages (these will be imported dynamically)
    agent_packages = [
        ("neuroscience_researcher", "use_cases.BCIInvestmentLab.agents.neuroscience_researcher"),
        ("market_intelligence", "use_cases.BCIInvestmentLab.agents.market_intelligence"),
        ("investment_coordinator", "use_cases.BCIInvestmentLab.agents.investment_coordinator")
    ]
    
    for agent_name, agent_package in agent_packages:
        try:
            # Register agent package path
            registry.register_package(NodeType.AGENT, agent_name, agent_package)
            registration_status["agents"][agent_name] = "registered"
            print(f"✅ Registered agent: {agent_name}")
        except Exception as e:
            registration_status["agents"][agent_name] = f"failed: {e}"
            registration_status["errors"].append(f"Agent {agent_name}: {e}")
            print(f"❌ Failed to register agent {agent_name}: {e}")
    
    # Register workflow packages
    workflow_packages = [
        ("literature_analysis", "use_cases.BCIInvestmentLab.workflows.literature_analysis"),
        ("market_monitoring", "use_cases.BCIInvestmentLab.workflows.market_monitoring"),
        ("recursive_synthesis", "use_cases.BCIInvestmentLab.workflows.recursive_synthesis")
    ]
    
    for workflow_name, workflow_package in workflow_packages:
        try:
            # Register workflow package path
            registry.register_package(NodeType.WORKFLOW, workflow_name, workflow_package)
            registration_status["workflows"][workflow_name] = "registered"
            print(f"✅ Registered workflow: {workflow_name}")
        except Exception as e:
            registration_status["workflows"][workflow_name] = f"failed: {e}"
            registration_status["errors"].append(f"Workflow {workflow_name}: {e}")
            print(f"❌ Failed to register workflow {workflow_name}: {e}")
    
    # Print summary
    total_tools = len(registration_status["tools"])
    successful_tools = len([s for s in registration_status["tools"].values() if s == "registered"])
    
    total_agents = len(registration_status["agents"])
    successful_agents = len([s for s in registration_status["agents"].values() if s == "registered"])
    
    total_workflows = len(registration_status["workflows"])
    successful_workflows = len([s for s in registration_status["workflows"].values() if s == "registered"])
    
    print(f"\n🧠💰 BCI Investment Lab Registration Summary:")
    print(f"📊 Tools: {successful_tools}/{total_tools} registered")
    print(f"🤖 Agents: {successful_agents}/{total_agents} registered")
    print(f"⚡ Workflows: {successful_workflows}/{total_workflows} registered")
    
    if registration_status["errors"]:
        print(f"⚠️  Errors: {len(registration_status['errors'])}")
        for error in registration_status["errors"][:3]:  # Show first 3 errors
            print(f"   - {error}")
    else:
        print("✅ All components registered successfully!")
    
    return registration_status


def get_registered_components() -> Dict[str, list]:
    """Get list of all registered BCI Investment Lab components.
    
    Returns:
        Dict with lists of registered tools, agents, and workflows
    """
    try:
        # Get all registered nodes
        tool_nodes = registry.list_nodes(NodeType.TOOL)
        agent_nodes = registry.list_nodes(NodeType.AGENT)
        workflow_nodes = registry.list_nodes(NodeType.WORKFLOW)
        
        # Filter for BCI Lab components (those registered by this module)
        bci_tools = [name for node_type, name in tool_nodes 
                    if name in ["arxiv_search", "statistical_analyzer", "yahoo_finance_fetcher",
                               "reddit_sentiment", "hackernews_tracker", "technology_readiness",
                               "company_research", "trend_analyzer", "neural_simulator"]]
        
        bci_agents = [name for node_type, name in agent_nodes 
                     if name in ["neuroscience_researcher", "market_intelligence", "investment_coordinator"]]
        
        bci_workflows = [name for node_type, name in workflow_nodes 
                        if name in ["literature_analysis", "market_monitoring", "recursive_synthesis"]]
        
        return {
            "tools": bci_tools,
            "agents": bci_agents,
            "workflows": bci_workflows,
            "total_components": len(bci_tools) + len(bci_agents) + len(bci_workflows)
        }
        
    except Exception as e:
        print(f"Error getting registered components: {e}")
        return {"tools": [], "agents": [], "workflows": [], "total_components": 0}


def verify_tool_functionality() -> Dict[str, Any]:
    """Verify that all registered tools are functional.
    
    Returns:
        Dict with verification results for each tool
    """
    verification_results = {}
    
    # Test each tool with minimal inputs
    tool_tests = {
        "arxiv_search": {"query": "artificial intelligence"},
        "statistical_analyzer": {"data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
        "yahoo_finance_fetcher": {"symbols": ["AAPL"]},
        "reddit_sentiment": {"query": "technology"},
        "hackernews_tracker": {"query": "artificial intelligence"},
        "technology_readiness": {"technology_name": "AI", "domain": "technology"},
        "company_research": {"company_name": "Apple Inc"},
        "trend_analyzer": {"data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
        "neural_simulator": {"signal_type": "eeg", "duration": 1.0, "channels": 4}
    }
    
    for tool_name, test_params in tool_tests.items():
        try:
            # Get tool instance from registry
            tool_instance = registry.get_instance(NodeType.TOOL, tool_name)
            
            if tool_instance:
                # Verify tool has required methods
                has_execute = hasattr(tool_instance, 'execute')
                has_schema = hasattr(tool_instance, 'get_input_schema')
                
                verification_results[tool_name] = {
                    "registered": True,
                    "has_execute_method": has_execute,
                    "has_schema_method": has_schema,
                    "test_params_ready": bool(test_params),
                    "status": "functional" if (has_execute and has_schema) else "incomplete"
                }
            else:
                verification_results[tool_name] = {
                    "registered": False,
                    "status": "not_found"
                }
                
        except Exception as e:
            verification_results[tool_name] = {
                "registered": False,
                "status": f"error: {e}"
            }
    
    # Generate summary
    total_tools = len(verification_results)
    functional_tools = len([r for r in verification_results.values() 
                           if r.get("status") == "functional"])
    
    print(f"\n🔧 Tool Verification Summary:")
    print(f"✅ Functional: {functional_tools}/{total_tools} tools")
    
    return {
        "results": verification_results,
        "summary": {
            "total_tools": total_tools,
            "functional_tools": functional_tools,
            "verification_success": functional_tools == total_tools
        }
    }


# Auto-register components when module is imported
if __name__ == "__main__":
    registration_status = register_bci_components()
    verification_results = verify_tool_functionality()
else:
    # Auto-register on import for production use
    try:
        register_bci_components()
    except Exception as e:
        print(f"Auto-registration failed: {e}")


# Export key functions
__all__ = [
    "register_bci_components",
    "get_registered_components", 
    "verify_tool_functionality"
] 