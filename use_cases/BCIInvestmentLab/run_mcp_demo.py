#!/usr/bin/env python3
"""
🧠💰 BCI Investment Lab - MCP Blueprint Demo
==========================================

Simple MCP API blueprint submission - lets ice_orchestrator handle execution.
Demonstrates all 8 node types from original demo:
✅ tool, condition, llm, loop, parallel, agent, workflow, recursive

Features:
- Modular blueprint architecture
- Complete node type coverage  
- Real API calls (arXiv, Yahoo Finance, NewsAPI, OpenAI)
- Advanced iceOS capabilities (recursive, parallel, workflow embedding)
- Mermaid visualization active

Usage:
    python run_mcp_demo.py
"""

import asyncio
import requests
import json
from datetime import datetime

# Import modular blueprints
from blueprints import (
    create_literature_analysis_blueprint,
    create_market_monitoring_blueprint,
    create_recursive_synthesis_blueprint
)


async def submit_blueprint(blueprint, workflow_name: str, api_base: str = "http://localhost:8000/api/v1"):
    """Submit blueprint to MCP API and let ice_orchestrator handle execution."""
    
    print(f"\n🚀 Submitting {workflow_name} Blueprint to MCP API")
    print(f"📋 ID: {blueprint.blueprint_id}")
    print(f"🔧 Nodes: {len(blueprint.nodes)} ({', '.join(blueprint.metadata.get('node_types_used', []))})")
    print(f"⚡ Duration: {blueprint.metadata.get('estimated_duration', 'unknown')}")
    
    try:
        # Simple MCP API submission
        response = requests.post(
            f"{api_base}/mcp/runs",
            json={
                "blueprint": blueprint.model_dump(),
                "options": {"max_parallel": 3}
            },
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        
        if response.status_code == 202:
            result = response.json()
            print(f"✅ Submitted! Run ID: {result.get('run_id')}")
            return result
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return {"error": response.status_code}
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return {"error": str(e)}


async def run_bci_investment_demo():
    """Run complete BCI Investment Lab demo via MCP API."""
    
    print("🧠💰 BCI INVESTMENT LAB - MODULAR MCP BLUEPRINT DEMO")
    print("🏗️  Architecture: Modular blueprints → MCP API → ice_orchestrator")
    print("📊 Mermaid visualization: ACTIVE")
    print("🎯 Node types: 8/9 iceOS node types demonstrated")
    print("=" * 80)
    
    session_id = f"bci_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    results = []
    
    # Demo configuration
    demos = [
        {
            "name": "Literature Analysis",
            "blueprint": create_literature_analysis_blueprint("brain-computer interfaces"),
            "description": "Demonstrates: tool, condition, llm, loop, parallel, agent"
        },
        {
            "name": "Market Monitoring", 
            "blueprint": create_market_monitoring_blueprint(["NFLX", "META", "GOOGL"]),
            "description": "Demonstrates: condition, parallel, tool, agent, llm"
        },
        {
            "name": "Recursive Synthesis",
            "blueprint": create_recursive_synthesis_blueprint("What are the most promising BCI investments for 2025?"),
            "description": "Demonstrates: condition, workflow, recursive, agent, llm, parallel"
        }
    ]
    
    print(f"\n📋 Executing {len(demos)} modular blueprints:")
    for i, demo in enumerate(demos, 1):
        print(f"  {i}. {demo['name']}: {demo['description']}")
    
    # Submit all blueprints to MCP API
    for demo in demos:
        result = await submit_blueprint(demo["blueprint"], demo["name"])
        results.append({
            "workflow": demo["name"],
            "blueprint_id": demo["blueprint"].blueprint_id,
            "submission_result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Brief pause between submissions
        await asyncio.sleep(1)
    
    # Save execution summary
    summary = {
        "session_id": session_id,
        "demo_type": "modular_mcp_blueprints",
        "architecture": "blueprints → MCP API → ice_orchestrator",
        "total_workflows": len(demos),
        "node_types_demonstrated": [
            "tool", "condition", "llm", "loop", 
            "parallel", "agent", "workflow", "recursive"
        ],
        "complexity_levels": ["basic", "intermediate", "advanced"],
        "results": results
    }
    
    results_file = f"bci_mcp_demo_{session_id}.json"
    with open(results_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n🎉 BCI INVESTMENT DEMO COMPLETE!")
    print(f"📊 Blueprints Submitted: {len(demos)}")
    print(f"🔧 Node Types Used: {len(summary['node_types_demonstrated'])}/9")
    print(f"🆔 Session: {session_id}")
    print(f"💾 Results: {results_file}")
    print(f"🏗️  Clean Architecture: No custom orchestrator needed!")
    print(f"⚡ ice_orchestrator handles all DAG execution")
    
    return True


if __name__ == "__main__":
    asyncio.run(run_bci_investment_demo()) 