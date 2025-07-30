"""Simple marketplace automation workflows using clean iceOS patterns."""

from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import (
    ToolNodeConfig, 
    AgentNodeConfig,
    LLMOperatorConfig,
    LLMConfig
)


def create_marketplace_automation_workflow() -> Workflow:
    """Create complete marketplace automation workflow using simple iceOS pattern.
    
    Returns:
        Configured workflow for end-to-end marketplace automation
    """
    
    nodes = [
        # 1. Read and process inventory
        ToolNodeConfig(
            id="read_inventory",
            type="tool",
            tool_name="read_inventory_csv",
            tool_args={
                "csv_file": "{{inputs.inventory_file}}"
            }
        ),
        
        # 2. Remove duplicates 
        ToolNodeConfig(
            id="dedupe_items",
            type="tool",
            tool_name="dedupe_items",
            tool_args={
                "clean_items": "{{read_inventory.items}}",
                "strategy": "keep_first"
            },
            dependencies=["read_inventory"]
        ),
        
        # 3. AI enhancement for better listings
        ToolNodeConfig(
            id="ai_enhance",
            type="tool", 
            tool_name="ai_enrichment",
            tool_args={
                "clean_items": "{{dedupe_items.clean_items}}",
                "model_name": "gpt-4o-mini"
            },
            dependencies=["dedupe_items"]
        ),
        
        # 4. Publish to marketplace
        ToolNodeConfig(
            id="publish_listings",
            type="tool",
            tool_name="facebook_publisher", 
            tool_args={
                "enhanced_items": "{{ai_enhance.enhanced_items}}"
            },
            dependencies=["ai_enhance"]
        ),
        
        # 5. Simulate marketplace activity
        ToolNodeConfig(
            id="simulate_activity",
            type="tool",
            tool_name="activity_simulator",
            tool_args={
                "activity_type": "all",
                "duration_minutes": 5,
                "listings": "{{publish_listings.published_items}}"
            },
            dependencies=["publish_listings"]
        ),
        
        # 6. Customer service agent handles inquiries
        AgentNodeConfig(
            id="customer_service",
            type="agent",
            package="use_cases.RivaRidge.FB_Marketplace_Seller.agents.customer_service_agent",
            agent_attr="CustomerServiceAgent",
            agent_config={
                "enable_memory": True
            },
            dependencies=["simulate_activity"]
        ),
        
        # 7. Pricing optimization agent
        AgentNodeConfig(
            id="pricing_optimization",
            type="agent",
            package="use_cases.RivaRidge.FB_Marketplace_Seller.agents.pricing_agent", 
            agent_attr="PricingAgent",
            agent_config={
                "enable_memory": True
            },
            dependencies=["customer_service"]
        ),
        
        # 8. Final summary
        LLMOperatorConfig(
            id="generate_summary",
            type="llm",
            model="gpt-4o",
            prompt="""Generate marketplace automation summary:

Inventory Processed: {{read_inventory.total_items}} items
Items Published: {{publish_listings.published_count}} listings
Customer Messages: {{simulate_activity.summary.total_messages}}
Sales Generated: {{simulate_activity.summary.total_sales}}
Pricing Adjustments: {{pricing_optimization.prices_updated}}

Provide a comprehensive summary of the automation results.""",
            llm_config=LLMConfig(
                model="gpt-4o",
                temperature=0.3
            ),
            dependencies=["pricing_optimization"]
        )
    ]
    
    # Create workflow with proper iceOS pattern
    workflow = Workflow(
        nodes=nodes,
        name="marketplace_automation",
        version="1.0.0",
        max_parallel=2,
        failure_policy="continue_possible"
    )
    
    return workflow


def create_simple_listing_workflow() -> Workflow:
    """Create simplified workflow for basic listing creation.
    
    Returns:
        Lightweight workflow for quick item listing
    """
    
    nodes = [
        # Simple CSV processing
        ToolNodeConfig(
            id="read_csv",
            type="tool",
            tool_name="read_inventory_csv",
            tool_args={
                "csv_file": "{{inputs.inventory_file}}"
            }
        ),
        
        # Basic enhancement
        ToolNodeConfig(
            id="enhance_items",
            type="tool",
            tool_name="ai_enrichment", 
            tool_args={
                "clean_items": "{{read_csv.items}}",
                "model_name": "gpt-4o-mini"
            },
            dependencies=["read_csv"]
        ),
        
        # Publish listings
        ToolNodeConfig(
            id="publish",
            type="tool",
            tool_name="facebook_publisher",
            tool_args={
                "enhanced_items": "{{enhance_items.enhanced_items}}"
            },
            dependencies=["enhance_items"]
        )
    ]
    
    workflow = Workflow(
        nodes=nodes,
        name="simple_listing",
        version="1.0.0"
    )
    
    return workflow


# Export workflows
__all__ = ["create_marketplace_automation_workflow", "create_simple_listing_workflow"] 