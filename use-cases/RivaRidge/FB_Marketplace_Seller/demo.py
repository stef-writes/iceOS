"""
Facebook Marketplace Seller Demo - Simple iceOS Workflow

This demonstrates iceOS's AI-powered workflow orchestration using a real-world
Facebook Marketplace automation use case.
"""

import asyncio
import os
from pathlib import Path

# Import our tools
from tools.read_inventory_csv import ReadInventoryCSVTool
from tools.dedupe_items import DedupeItemsTool  
from tools.ai_enrichment import AIEnrichmentTool
from tools.facebook_publisher import FacebookPublisherTool

# Import iceOS components
from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import ToolNodeConfig
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType


async def register_demo_tools():
    """Register our custom tools with iceOS registry."""
    
    print("🔧 Registering Facebook Marketplace tools...")
    
    # Register each tool instance
    tools = [
        ReadInventoryCSVTool(),
        DedupeItemsTool(),
        AIEnrichmentTool(), 
        FacebookPublisherTool()
    ]
    
    for tool in tools:
        try:
            registry.register_instance(NodeType.TOOL, tool.name, tool)
            print(f"   ✅ Registered: {tool.name}")
        except Exception as e:
            print(f"   ⚠️  Tool {tool.name} already registered: {e}")
    
    print("🔧 Tool registration complete!")


async def create_marketplace_workflow():
    """Create a 4-step Facebook Marketplace workflow."""
    
    # Current directory and inventory file
    current_dir = Path(__file__).parent
    inventory_file = current_dir / "inventory.csv"
    
    # Step 1: Read CSV inventory
    read_csv_node = ToolNodeConfig(
        id="read_csv",
        tool_name="read_inventory_csv",
        tool_args={"csv_file": str(inventory_file)},
        dependencies=[]
    )
    
    # Step 2: Remove duplicates
    dedupe_node = ToolNodeConfig(
        id="dedupe",
        tool_name="dedupe_items", 
        tool_args={"strategy": "keep_first"},
        dependencies=["read_csv"]
    )
    
    # Step 3: AI enrichment with real LLM calls
    ai_enrich_node = ToolNodeConfig(
        id="ai_enrich",
        tool_name="ai_enrichment",
        tool_args={"model_name": "gpt-4o-mini"},
        dependencies=["dedupe"]
    )
    
    # Step 4: Publish to Facebook Marketplace
    publish_node = ToolNodeConfig(
        id="publish",
        tool_name="facebook_publisher",
        tool_args={"auto_publish": True},
        dependencies=["ai_enrich"]
    )
    
    # Create workflow
    workflow = Workflow(
        nodes=[read_csv_node, dedupe_node, ai_enrich_node, publish_node],
        name="Facebook Marketplace Seller Pipeline",
        chain_id="fb_marketplace_demo"
    )
    
    return workflow


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


def print_results(result):
    """Print workflow results in a nice format."""
    
    print("\n" + "="*80)
    print("🎉 FACEBOOK MARKETPLACE SELLER DEMO COMPLETE!")
    print("="*80)
    
    if isinstance(result, dict):
        # Look for individual node results
        for node_id, node_result in result.items():
            if isinstance(node_result, dict):
                print(f"\n📊 {node_id.upper()} RESULTS:")
                print("-" * 40)
                
                # Print key metrics
                for key, value in node_result.items():
                    if key in ['success', 'items_imported', 'items_after_dedup', 'items_processed', 
                              'llm_calls_made', 'items_published', 'estimated_reach', 'total_estimated_value']:
                        print(f"   {key}: {value}")
    
    print("\n🚀 This demonstrates iceOS's:")
    print("   • AI-powered workflow orchestration")
    print("   • Real LLM integration for content optimization") 
    print("   • Tool composition and data flow")
    print("   • Multi-step marketplace automation")
    print("\n💡 Perfect foundation for building complex AI agents!")


async def main():
    """Run the Facebook Marketplace Seller demo."""
    
    print("🚀 Facebook Marketplace Seller Demo")
    print("   Powered by iceOS AI Workflow Orchestration")
    print("="*60)
    
    try:
        # Load environment for LLM access
        await load_environment()
        
        # Initialize iceOS orchestrator services
        print("🔧 Initializing iceOS orchestrator...")
        from ice_orchestrator import initialize_orchestrator
        initialize_orchestrator()
        print("✅ iceOS services initialized!")
        
        # Register our custom tools
        await register_demo_tools()
        
        # Create and run workflow
        print("\n🔄 Creating workflow...")
        workflow = await create_marketplace_workflow()
        
        print("🔄 Executing workflow...")
        result = await workflow.execute()
        
        # Display results
        print_results(result)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 