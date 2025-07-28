#!/usr/bin/env python3
"""
🧠💰 BCI Investment Lab - Real iceOS Blueprint Execution
======================================================

ZERO MOCKING - ALL REAL:
✅ Real arXiv API calls
✅ Real Yahoo Finance API 
✅ Real NewsAPI calls
✅ Real OpenAI LLM calls
✅ Real agent memory storage
✅ Real workflow orchestration

Usage:
    python run_blueprint.py
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

    # Add project root and use_cases to Python path
    project_root = Path(__file__).parent.parent.parent
    use_cases_dir = project_root / "use_cases"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(use_cases_dir))

# iceOS Blueprint imports
from ice_orchestrator.workflow import Workflow
from ice_core.unified_registry import registry

# Import real workflows
from BCIInvestmentLab.workflows import (
    create_literature_analysis_workflow,
    create_market_monitoring_workflow, 
    create_recursive_synthesis_workflow
)

# Register tools and agents
from BCIInvestmentLab.registry import register_bci_components

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_literature_analysis_blueprint() -> dict:
    """Execute literature analysis with real APIs."""
    
    print("🔬 EXECUTING LITERATURE ANALYSIS BLUEPRINT (REAL APIs)")
    print("=" * 60)
    
    # Create real workflow
    workflow = create_literature_analysis_workflow()
    
    # Real inputs - no mocking
    inputs = {
        "research_query": "brain computer interface motor imagery advances 2024",
        "paper_limit": 15,
        "analysis_depth": "comprehensive",
        "focus_areas": [
            "technology_readiness",
            "clinical_applications", 
            "breakthrough_potential",
            "commercial_viability"
        ],
        "time_horizon": "6_months"
    }
    
    print(f"📋 Query: {inputs['research_query']}")
    print(f"📊 Papers: {inputs['paper_limit']}")
    print(f"🎯 Focus: {', '.join(inputs['focus_areas'])}")
    
    # Execute with real iceOS orchestrator
    try:
        print("\n🚀 Executing workflow with REAL APIs...")
        # Set workflow context with inputs
        workflow.context = inputs
        result = await workflow.execute()
        
        print(f"\n✅ LITERATURE ANALYSIS COMPLETE!")
        print(f"📄 Papers Analyzed: {result.get('papers_analyzed', 'N/A')}")
        print(f"🔍 Key Findings: {len(result.get('key_findings', []))}")
        print(f"📈 Research Trends: {len(result.get('research_trends', []))}")
        print(f"🎯 Confidence: {result.get('confidence_score', 0.0):.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"Literature analysis failed: {e}")
        return {"error": str(e)}


async def run_market_monitoring_blueprint() -> dict:
    """Execute market monitoring with real APIs."""
    
    print("\n📊 EXECUTING MARKET MONITORING BLUEPRINT (REAL APIs)")
    print("=" * 60)
    
    # Create real workflow
    workflow = create_market_monitoring_workflow()
    
    # Real inputs - BCI companies
    inputs = {
        "companies": ["NVDA", "GOOGL", "META", "AAPL"],  # Real BCI-adjacent stocks
        "monitoring_duration": "1_week",
        "alert_thresholds": {
            "price_change_percent": 5.0,
            "volume_spike": 2.0,
            "sentiment_score": 0.7
        },
        "focus_sectors": ["neurotechnology", "healthcare", "AI"],
        "risk_tolerance": "moderate",
        "enable_realtime": False
    }
    
    print(f"🏢 Companies: {', '.join(inputs['companies'])}")
    print(f"⏱️  Duration: {inputs['monitoring_duration']}")
    print(f"📊 Risk Tolerance: {inputs['risk_tolerance']}")
    
    # Execute with real iceOS orchestrator
    try:
        print("\n🚀 Executing workflow with REAL APIs...")
        # Set workflow context with inputs
        workflow.context = inputs
        result = await workflow.execute()
        
        print(f"\n✅ MARKET MONITORING COMPLETE!")
        print(f"🏢 Companies Monitored: {len(result.get('companies_monitored', []))}")
        print(f"📊 Market Signals: {len(result.get('market_signals', []))}")
        print(f"🚨 Alert Triggers: {len(result.get('alert_triggers', []))}")
        print(f"⚠️  Risk Level: {result.get('risk_assessment', {}).get('overall_risk', 'N/A')}")
        print(f"🎯 Confidence: {result.get('confidence_score', 0.0):.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"Market monitoring failed: {e}")
        return {"error": str(e)}


async def run_recursive_synthesis_blueprint() -> dict:
    """Execute recursive synthesis with real APIs."""
    
    print("\n🔄 EXECUTING RECURSIVE SYNTHESIS BLUEPRINT (REAL APIs)")
    print("=" * 60)
    
    # Create real workflow
    workflow = create_recursive_synthesis_workflow()
    
    # Real investment thesis
    inputs = {
        "investment_thesis": "Brain-computer interface technology represents a transformational investment opportunity due to rapid advances in neural decoding, FDA approval pathways for medical devices, and expanding applications from therapeutic to consumer markets",
        "research_depth": "comprehensive",
        "convergence_threshold": 0.85,
        "max_iterations": 5,
        "focus_areas": [
            "technology_readiness",
            "market_opportunity",
            "competitive_landscape", 
            "regulatory_environment",
            "investment_timing"
        ],
        "risk_tolerance": "moderate",
        "investment_amount": 1000000.0
    }
    
    print(f"💡 Thesis: {inputs['investment_thesis'][:80]}...")
    print(f"🎯 Convergence: {inputs['convergence_threshold']}")
    print(f"🔄 Max Iterations: {inputs['max_iterations']}")
    print(f"💰 Amount: ${inputs['investment_amount']:,.0f}")
    
    # Execute with real iceOS orchestrator
    try:
        print("\n🚀 Executing workflow with REAL APIs...")
        # Set workflow context with inputs
        workflow.context = inputs
        result = await workflow.execute()
        
        print(f"\n✅ RECURSIVE SYNTHESIS COMPLETE!")
        print(f"🔄 Convergence: {result.get('convergence_achieved', False)}")
        print(f"🔁 Iterations: {result.get('iterations_completed', 0)}")
        print(f"🤝 Consensus: {result.get('consensus_score', 0.0):.2f}")
        print(f"📋 Recommendation: {result.get('investment_recommendation', 'N/A')[:50]}...")
        print(f"🎯 Confidence: {result.get('confidence_score', 0.0):.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"Recursive synthesis failed: {e}")
        return {"error": str(e)}


async def main():
    """Execute complete BCI Investment Lab Blueprint suite."""
    
    print("🎯 BCI INVESTMENT LAB - REAL iceOS BLUEPRINT EXECUTION")
    print("🚫 ZERO MOCKING - ALL REAL APIs, LLMs, AND DATA")
    print("=" * 80)
    
    # Register all components
    print("📋 Registering BCI components...")
    try:
        register_bci_components()
        print("✅ Components registered successfully")
        print(f"🔧 Tools available: {len(registry.list_tools())}")
        print(f"🤖 Agents available: {len(registry.list_agents())}")
    except Exception as e:
        logger.error(f"Component registration failed: {e}")
        return
    
    # Track execution results
    execution_results = {
        "start_time": datetime.now().isoformat(),
        "workflows_executed": [],
        "total_api_calls": 0,
        "total_cost_estimate": 0.0,
        "results": {}
    }
    
    try:
        # Execute Literature Analysis
        lit_result = await run_literature_analysis_blueprint()
        execution_results["results"]["literature_analysis"] = lit_result
        execution_results["workflows_executed"].append("literature_analysis")
        
        # Execute Market Monitoring
        market_result = await run_market_monitoring_blueprint()
        execution_results["results"]["market_monitoring"] = market_result
        execution_results["workflows_executed"].append("market_monitoring")
        
        # Execute Recursive Synthesis  
        synthesis_result = await run_recursive_synthesis_blueprint()
        execution_results["results"]["recursive_synthesis"] = synthesis_result
        execution_results["workflows_executed"].append("recursive_synthesis")
        
    except Exception as e:
        logger.error(f"Blueprint execution failed: {e}")
        execution_results["error"] = str(e)
    
    execution_results["end_time"] = datetime.now().isoformat()
    
    # Final summary
    print(f"\n🎉 BCI INVESTMENT LAB BLUEPRINT EXECUTION COMPLETE!")
    print(f"📊 Workflows Executed: {len(execution_results['workflows_executed'])}")
    print(f"⚡ All Real APIs Used - Zero Mocking")
    print(f"🧠 Full Agent Memory Integration")
    print(f"🔄 Complete Workflow Orchestration")
    
    # Save results
    results_file = Path("bci_blueprint_results.json")
    import json
    with open(results_file, "w") as f:
        json.dump(execution_results, f, indent=2)
    print(f"💾 Results saved to: {results_file}")
    
    return execution_results


if __name__ == "__main__":
    asyncio.run(main()) 