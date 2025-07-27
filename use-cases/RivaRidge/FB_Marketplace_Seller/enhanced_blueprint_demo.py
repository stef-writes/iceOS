"""
Enhanced Facebook Marketplace Seller Demo - Blueprint/MCP Approach

This demonstrates the full iceOS 3-tier architecture:
1. Blueprint construction (design-time)
2. MCP validation and governance (compile-time) 
3. Orchestrator execution (runtime)

Features showcased:
- Agent nodes with memory systems
- Loop nodes for continuous monitoring
- Condition nodes for intelligent routing
- Complex tool orchestration
- Blueprint validation and optimization
- 🆕 Real HTTP API calls (facebook_api_client)
- 🆕 Realistic marketplace activity simulation (activity_simulator)
- 🆕 Complete ecosystem demonstration with live network requests
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any

# Import iceOS MCP components
from ice_core.models.mcp import Blueprint, NodeSpec
from ice_api.api.mcp import create_blueprint, start_run
from ice_core.models.mcp import RunRequest
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType

# Import our tools (including new agent tools and realistic features)
from tools.read_inventory_csv import ReadInventoryCSVTool
from tools.dedupe_items import DedupeItemsTool  
from tools.ai_enrichment import AIEnrichmentTool
from tools.facebook_publisher import FacebookPublisherTool
from tools.facebook_api_client import FacebookAPIClientTool  # NEW: Real HTTP API calls
from tools.activity_simulator import ActivitySimulatorTool  # NEW: Realistic marketplace activities
from tools.inquiry_responder import InquiryResponderTool
from tools.market_research import MarketResearchTool
from tools.facebook_messenger import FacebookMessengerTool
from tools.price_updater import PriceUpdaterTool


async def register_demo_tools():
    """Register our custom tools with iceOS registry."""
    
    print("🔧 Registering Facebook Marketplace tools...")
    
    # Register each tool instance
    tools = [
        ReadInventoryCSVTool(),
        DedupeItemsTool(),
        AIEnrichmentTool(), 
        FacebookPublisherTool(),
        FacebookAPIClientTool(),      # NEW: Real HTTP API calls
        ActivitySimulatorTool(),      # NEW: Realistic marketplace activities
        InquiryResponderTool(),
        MarketResearchTool(),
        FacebookMessengerTool(),
        PriceUpdaterTool()
    ]
    
    for tool in tools:
        registry.register_instance(NodeType.TOOL, tool.name, tool)
        print(f"   ✅ Registered: {tool.name}")
    
    print("🔧 Tool registration complete!")


async def create_enhanced_blueprint() -> Blueprint:
    """Create enhanced blueprint with agents, memory, and control flow."""
    
    current_dir = Path(__file__).parent
    inventory_file = current_dir / "inventory.csv"
    
    # Define the enhanced workflow blueprint
    blueprint = Blueprint(
        blueprint_id="fb_marketplace_enhanced",
        schema_version="1.1.0",
        nodes=[
            # Phase 1: Data Pipeline (same as before)
            NodeSpec(
                id="read_csv",
                type="tool",
                tool_name="read_inventory_csv",
                tool_args={"csv_file": str(inventory_file)},
                dependencies=[]
            ),
            NodeSpec(
                id="dedupe",
                type="tool", 
                tool_name="dedupe_items",
                tool_args={"strategy": "keep_first"},
                dependencies=["read_csv"]
            ),
            NodeSpec(
                id="ai_enrich",
                type="tool",
                tool_name="ai_enrichment", 
                tool_args={"model_name": "gpt-4o"},  # Use allowed model from registry
                # Alternative providers (requires proper API keys):
                # "model_name": "claude-3-haiku-20240307"  # Anthropic
                # "model_name": "gemini-pro"               # Google  
                # "model_name": "deepseek-chat"            # DeepSeek
                dependencies=["dedupe"]
            ),
            NodeSpec(
                id="publish",
                type="tool",
                tool_name="facebook_publisher",
                tool_args={"auto_publish": True},
                dependencies=["ai_enrich"]
            ),
            
            # Phase 1.5: NEW REALISTIC FEATURES 🚀
            NodeSpec(
                id="real_api_publish",
                type="tool",
                tool_name="facebook_api_client",
                tool_args={"action": "create_listing"},
                dependencies=["publish"]
            ),
            NodeSpec(
                id="simulate_activity",
                type="tool", 
                tool_name="activity_simulator",
                tool_args={"activity_type": "all", "duration_minutes": 2},
                dependencies=["real_api_publish"]
            ),
            NodeSpec(
                id="get_messages",
                type="tool",
                tool_name="facebook_api_client", 
                tool_args={"action": "get_messages"},
                dependencies=["simulate_activity"]
            ),
            
            # Phase 2: Customer Service Agent with Memory
            NodeSpec(
                id="customer_service_agent",
                type="agent",
                package="use_cases.RivaRidge.FB_Marketplace_Seller.agents.customer_service_agent",
                tools=[
                    {
                        "name": "inquiry_responder",
                        "description": "Generates intelligent responses to customer inquiries",
                        "parameters": {},
                        "required": []
                    },
                    {
                        "name": "facebook_messenger", 
                        "description": "Sends messages via Facebook Messenger",
                        "parameters": {},
                        "required": []
                    }
                ],
                memory={
                    "enable_episodic": True,   # Remember conversations
                    "enable_semantic": True,   # Learn from interactions  
                    "enable_working": True,    # Active conversation state
                    "ttl_seconds": 86400,      # 24 hour memory
                    "max_entries": 1000
                },
                input_schema={
                    "type": "object",
                    "properties": {
                        "inquiry": {"type": "string", "description": "Customer inquiry text"},
                        "customer_id": {"type": "string", "description": "Customer identifier"}
                    },
                    "required": ["inquiry", "customer_id"]
                },
                output_schema={
                    "type": "object", 
                    "properties": {
                        "response": {"type": "string", "description": "Generated response"},
                        "confidence": {"type": "number", "description": "Response confidence 0-1"},
                        "needs_human": {"type": "boolean", "description": "Whether human intervention needed"}
                    },
                    "required": ["response", "confidence"]
                },
                dependencies=["get_messages"]  # Now connects after realistic marketplace activities
            ),
            
            # Phase 3: Continuous Monitoring Loop
            NodeSpec(
                id="inquiry_monitor",
                type="loop",
                items_source="facebook_notifications", 
                body_nodes=["customer_service_agent"],
                max_iterations=100,
                parallel=False,
                input_schema={
                    "type": "object",
                    "properties": {
                        "facebook_notifications": {"type": "array", "description": "List of customer notifications"}
                    },
                    "required": ["facebook_notifications"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "iterations_completed": {"type": "number", "description": "Number of loop iterations"},
                        "inquiries_processed": {"type": "number", "description": "Total inquiries handled"}
                    },
                    "required": ["iterations_completed"]
                },
                dependencies=["customer_service_agent"]
            ),
            
            # Phase 4: Pricing Analysis Condition
            NodeSpec(
                id="sales_check",
                type="condition",
                expression="len(completed_sales) >= 5",  # After 5 sales
                true_branch=["pricing_optimizer"],
                false_branch=[],
                input_schema={
                    "type": "object",
                    "properties": {
                        "completed_sales": {"type": "array", "description": "List of completed sales"}
                    },
                    "required": ["completed_sales"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "boolean", "description": "Condition evaluation result"},
                        "branch_taken": {"type": "string", "description": "Which branch was executed"}
                    },
                    "required": ["result"]
                },
                dependencies=["inquiry_monitor"]
            ),
            
            # Phase 5: Pricing Optimization Agent
            NodeSpec(
                id="pricing_optimizer",
                type="agent",
                package="use_cases.RivaRidge.FB_Marketplace_Seller.agents.pricing_agent",
                tools=[
                    {
                        "name": "market_research",
                        "description": "Researches competitor pricing and market trends",
                        "parameters": {},
                        "required": []
                    },
                    {
                        "name": "price_updater",
                        "description": "Updates listing prices based on recommendations", 
                        "parameters": {},
                        "required": []
                    }
                ],
                memory={
                    "enable_procedural": True,  # Learn pricing strategies
                    "enable_semantic": True,    # Remember market data
                    "ttl_seconds": 604800      # 7 day memory for pricing data
                },
                input_schema={
                    "type": "object",
                    "properties": {
                        "completed_sales": {"type": "array", "description": "List of completed sales"},
                        "current_listings": {"type": "array", "description": "Current active listings"}
                    },
                    "required": ["completed_sales", "current_listings"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "recommendations": {"type": "object", "description": "Pricing recommendations"},
                        "prices_updated": {"type": "number", "description": "Number of prices updated"},
                        "confidence": {"type": "number", "description": "Recommendation confidence 0-1"}
                    },
                    "required": ["recommendations", "prices_updated"]
                },
                dependencies=[]  # Only runs when condition is met
            )
        ],
        metadata={
            "demo_type": "enhanced_marketplace_automation",
            "features": [
                "agent_with_memory", 
                "continuous_monitoring",
                "conditional_execution", 
                "multi_agent_coordination"
            ],
            "estimated_cost_per_run": "$0.25",
            "estimated_duration": "continuous"
        }
    )
    
    return blueprint


async def validate_and_execute_blueprint(blueprint: Blueprint) -> Dict[str, Any]:
    """Use MCP validation tier to validate and execute blueprint."""
    
    print("🔍 Validating blueprint through MCP tier...")
    
    # Step 1: Create/register blueprint (validates structure)
    try:
        ack = await create_blueprint(blueprint)
        print(f"✅ Blueprint validated and registered: {ack.blueprint_id}")
        print(f"📋 Status: {ack.status}")
    except Exception as e:
        print(f"❌ Blueprint validation failed: {e}")
        return {"success": False, "error": str(e)}
    
    # Step 2: Start execution through MCP
    print("\n🚀 Starting execution through MCP tier...")
    
    try:
        run_request = RunRequest(
            blueprint_id=blueprint.blueprint_id
        )
        
        run_ack = await start_run(run_request)
        print(f"✅ Execution started: {run_ack.run_id}")
        print(f"🔗 Status endpoint: {run_ack.status_endpoint}")
        print(f"📡 Events endpoint: {run_ack.events_endpoint}")
        
        return {
            "success": True,
            "blueprint_id": blueprint.blueprint_id,
            "run_id": run_ack.run_id,
            "status_endpoint": run_ack.status_endpoint
        }
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        return {"success": False, "error": str(e)}


async def run_sdk_workflow():
    """Execute using SDK WorkflowBuilder (LangChain/LangGraph style approach)."""
    
    print("🔧 Creating workflow using SDK WorkflowBuilder...")
    print("💡 This is the developer-friendly approach (like LangChain/LangGraph)")
    
    from ice_sdk.builders.workflow import WorkflowBuilder
    from pathlib import Path
    
    # Current directory and inventory file
    current_dir = Path(__file__).parent
    inventory_file = current_dir / "inventory.csv"
    
    # ✨ Enhanced Fluent API workflow with REAL HTTP calls and marketplace simulation!
    workflow = (WorkflowBuilder("FB Marketplace with Realistic Activities")
        # Phase 1: Data processing pipeline
        .add_tool("read_csv", "read_inventory_csv", csv_file=str(inventory_file))
        .add_tool("dedupe", "dedupe_items", strategy="keep_first") 
        .add_tool("ai_enrich", "ai_enrichment", model_name="gpt-4o")
        .add_tool("publish", "facebook_publisher", auto_publish=True)
        
        # Phase 2: NEW REALISTIC FEATURES 🚀
        .add_tool("real_api_publish", "facebook_api_client", 
                  action="create_listing")  # Real HTTP calls to create listings
        .add_tool("simulate_activity", "activity_simulator", 
                  activity_type="all", duration_minutes=2)  # Realistic marketplace activities
        .add_tool("get_messages", "facebook_api_client", 
                  action="get_messages")  # Real HTTP calls to get customer messages
        
        # Phase 3: Memory-enabled agents with enhanced tools
        .add_agent("customer_service", 
                  package="customer_service",  # Registered agent name
                  tools=["inquiry_responder", "facebook_messenger"],
                  memory={"enable_episodic": True, "enable_semantic": True, "enable_working": True})
        .add_agent("pricing_agent", 
                  package="pricing_optimizer",  # Registered agent name
                  tools=["market_research", "price_updater"],
                  memory={"enable_procedural": True, "enable_semantic": True})
        
        # Phase 4: Enhanced workflow connections for realistic marketplace experience
        .connect("read_csv", "dedupe")
        .connect("dedupe", "ai_enrich")
        .connect("ai_enrich", "publish")           # Basic publishing first
        .connect("publish", "real_api_publish")     # Then real HTTP API calls
        .connect("real_api_publish", "simulate_activity")  # Generate marketplace activities  
        .connect("simulate_activity", "get_messages")      # Get customer messages
        .connect("get_messages", "customer_service")       # Handle customer service
        .connect("customer_service", "pricing_agent")      # Optimize pricing
        
        .build()
    )
    
    print("✨ Built workflow using fluent SDK API")
    print("🧠 Agents have memory and tools enabled")
    print("🔗 Connected nodes in pipeline")
    
    # Execute directly through SDK
    print("🚀 Executing SDK workflow...")
    result = await workflow.execute()
    
    return {
        "success": True,
        "method": "sdk_workflow_builder",
        "result": result
    }


def print_blueprint_info(blueprint: Blueprint):
    """Print detailed information about the blueprint."""
    
    print("\n" + "="*80)
    print("🎨 ENHANCED FACEBOOK MARKETPLACE BLUEPRINT")
    print("="*80)
    
    print(f"📋 Blueprint ID: {blueprint.blueprint_id}")
    print(f"🔧 Schema Version: {blueprint.schema_version}")
    print(f"📊 Total Nodes: {len(blueprint.nodes)}")
    
    print("\n🏗️ Architecture Overview:")
    for i, node in enumerate(blueprint.nodes, 1):
        deps = f" (depends on: {', '.join(node.dependencies)})" if node.dependencies else ""
        print(f"   {i}. {node.id} [{node.type}]{deps}")
    
    print(f"\n💰 Estimated Cost: {blueprint.metadata.get('estimated_cost_per_run', 'Unknown')}")
    print(f"⏱️  Duration: {blueprint.metadata.get('estimated_duration', 'Unknown')}")
    
    print("\n🚀 Advanced Features Demonstrated:")
    features = blueprint.metadata.get('features', [])
    for feature in features:
        feature_desc = {
            'agent_with_memory': '🧠 Agents with persistent memory systems',
            'continuous_monitoring': '🔄 Loop nodes for real-time monitoring', 
            'conditional_execution': '🔀 Condition nodes for intelligent routing',
            'multi_agent_coordination': '🤝 Multiple agents working together'
        }
        print(f"   • {feature_desc.get(feature, feature)}")


def print_results(result: Dict[str, Any]):
    """Print execution results."""
    
    print("\n" + "="*80)
    print("🎉 ENHANCED BLUEPRINT DEMO COMPLETE!")
    print("="*80)
    
    if result.get("success"):
        print(f"✅ Blueprint Execution Successful!")
        print(f"📋 Blueprint ID: {result.get('blueprint_id')}")
        print(f"🚀 Run ID: {result.get('run_id')}")
        print(f"📊 Status: {result.get('status_endpoint')}")
    else:
        print(f"❌ Execution Failed: {result.get('error')}")
    
    print("\n🏆 This demonstrates iceOS's full 3-tier architecture:")
    print("   • 🎨 Blueprint design-time validation")
    print("   • 🛡️  MCP governance and optimization layer")
    print("   • ⚙️  Orchestrator runtime execution engine") 
    print("   • 🧠 Memory-enabled agents with learning")
    print("   • 🔄 Advanced control flow (loops, conditions)")
    print("   • 🤖 Multi-agent coordination and reasoning")
    
    print("\n💡 Perfect foundation for building production AI systems!")


async def load_environment():
    """Load environment variables for LLM access."""
    
    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    
    if env_file.exists():
        print(f"📝 Loading environment from: {env_file}")
        
        # Simple .env loader
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        
        print("📝 Environment loaded!")
    else:
        print("⚠️  No .env file found - LLM calls may fail")


async def main():
    """Compare both iceOS execution approaches."""
    
    print("🚀 Enhanced Facebook Marketplace Demo")
    print("   Comparing iceOS Execution Approaches")
    print("="*60)
    
    try:
        # Load environment and initialize
        await load_environment()
        
        print("🔧 Initializing iceOS orchestrator...")
        from ice_orchestrator import initialize_orchestrator
        initialize_orchestrator()
        print("✅ iceOS services initialized!")
        
        # Register tools and agents directly
        await register_demo_tools()  # Use the existing function that works
        
        # Register agents manually
        from ice_core.unified_registry import global_agent_registry
        global_agent_registry.register_agent(
            "customer_service",
            "use_cases.RivaRidge.FB_Marketplace_Seller.agents.customer_service_agent"
        )
        global_agent_registry.register_agent(
            "pricing_optimizer", 
            "use_cases.RivaRidge.FB_Marketplace_Seller.agents.pricing_agent"
        )
        
        print("\n" + "="*80)
        print("🎯 APPROACH 1: MCP Blueprint (Enterprise/Governance)")
        print("="*80)
        print("💼 Structured schema, validation, optimization, governance")
        
        # Method 1: MCP Blueprint approach
        blueprint = await create_enhanced_blueprint()
        mcp_result = await validate_and_execute_blueprint(blueprint)
        
        print("\n" + "="*80)
        print("🎯 APPROACH 2: SDK WorkflowBuilder (Developer Experience)")
        print("="*80)
        print("⚡ Fluent API, direct execution, LangChain/LangGraph style")
        
        # Method 2: SDK approach
        sdk_result = await run_sdk_workflow()
        
        # Compare approaches
        print("\n" + "="*80)
        print("📊 APPROACH COMPARISON")
        print("="*80)
        print(f"MCP Blueprint:     {'✅' if mcp_result.get('success') else '❌'} (Enterprise)")
        print(f"SDK WorkflowBuilder: {'✅' if sdk_result.get('success') else '❌'} (Developer)")
        print("\n💡 Both approaches run the same agents with memory and tools!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 