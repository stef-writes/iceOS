# Facebook Marketplace Seller Automation

A complete workflow automation system for managing Facebook Marketplace listings, from inventory analysis to customer communication, built using iceOS patterns.

## Project Structure

```
FB-Marketplace-Seller/
├── FBMSeller.py           # Main workflow orchestrator using WorkflowBuilder
├── __init__.py            # Package initialization
├── agents/                # Documentation about agents (actual agents in ice_sdk.agents)
│   └── __init__.py
├── tools/                 # Reusable tools implementing ToolBase
│   ├── __init__.py
│   ├── marketplace/       # Facebook Marketplace API tools
│   │   ├── __init__.py
│   │   ├── facebook_api_tool.py
│   │   └── price_research_tool.py
│   ├── inventory/         # Inventory management tools
│   │   ├── __init__.py
│   │   ├── inventory_analyzer_tool.py
│   │   └── image_enhancer_tool.py
│   ├── analytics/         # Analytics and reporting tools
│   └── communication/     # Messaging and notification tools
├── workflows/             # Pre-defined workflow templates
├── config/                # Configuration files
├── tests/                 # Unit and integration tests
└── docs/                  # Documentation
    └── AGENT_MEMORY_REQUIREMENTS.md
```

## Architecture

This use case follows iceOS patterns:
- **Tools**: Stateless operations that inherit from `ToolBase`
- **Agents**: Intelligent reasoning nodes referenced by package string
- **WorkflowBuilder**: Fluent API for constructing workflows
- **Unified Registry**: Automatic registration of tools and agents

## Quick Start

```python
from use_cases.RivaRidge.FB_Marketplace_Seller import FBMSeller

# Initialize the workflow
seller = FBMSeller(config={
    "marketplace": "facebook",
    "location": "Seattle, WA",
    "category": "Electronics",
    "min_value_threshold": 25.0
})

# Run with inventory data
results = await seller.run({
    "items": [
        {
            "id": "item-001",
            "name": "Laptop - Dell XPS 13",
            "condition": "Like New",
            "original_price": 1299.99,
            "quantity": 1
        }
    ]
})
```

## Workflow Phases

The workflow uses the `WorkflowBuilder` to create a DAG of operations:

1. **Inventory Analysis** (Tool) - Filter items suitable for listing
2. **Price Research** (Tool) - Analyze market prices
3. **Image Enhancement** (Tool) - Enhance product images (parallel with pricing)
4. **Listing Creation** (Agent) - AI-powered listing generation
5. **Message Monitoring** (Loop) - Monitor and respond to inquiries
6. **Metrics Tracking** (Tool) - Track performance metrics

## Key Components

### Tools
Tools are stateless operations that implement `ToolBase`:

- **InventoryAnalyzerTool**: Filters inventory based on conditions and value
- **FacebookAPITool**: Interfaces with Facebook Marketplace API
- **PriceResearchTool**: Analyzes market prices for competitive pricing
- **ImageEnhancerTool**: Enhances product images for better presentation

All tools are automatically registered with the unified registry.

### Agents
Agents provide intelligent reasoning and are registered in `ice_sdk.agents`:

- **marketplace_agent**: Creates optimized listings using AI
- **customer_service**: Handles customer interactions (TBD)

Agents are referenced by package string in workflows:
```python
builder.add_agent(
    node_id="listing_creator",
    package="ice_sdk.agents.marketplace_agent",
    tools=["facebook_api", "price_research"]
)
```

## Configuration

The system supports configuration at multiple levels:

```python
config = {
    "marketplace": "facebook",
    "location": "Seattle, WA",
    "categories": ["Electronics", "Home & Garden"],
    "min_value_threshold": 25.0,
    "condition_requirements": ["New", "Like New", "Good"],
    "auto_respond": True,
    "response_delay_minutes": 5
}
```

## Development

### Adding New Tools

1. Create a new tool class inheriting from `ToolBase`:
```python
from ice_core.base_tool import ToolBase

class MyNewTool(ToolBase):
    name = "my_new_tool"
    description = "Does something useful"
    
    async def _execute_impl(self, **kwargs):
        # Implementation
        return {"result": "success"}
```

2. Register in the appropriate `__init__.py`:
```python
registry.register_instance(NodeType.TOOL, "my_new_tool", MyNewTool())
```

### Adding New Agents

1. Create agent in `ice_sdk.agents/`:
```python
class MyAgent(AgentNode):
    def __init__(self):
        config = AgentNodeConfig(
            package="ice_sdk.agents.my_agent",
            # ... configuration
        )
        super().__init__(config=config)
```

2. Register in `ice_sdk.agents.__init__.py`:
```python
global_agent_registry["my_agent"] = "ice_sdk.agents.my_agent"
```

## Testing

Run tests with:
```bash
python -m pytest tests/
```

## Future Enhancements

- [ ] Multi-marketplace support (OfferUp, Craigslist, etc.)
- [ ] Advanced pricing algorithms using ML
- [ ] Automated negotiation handling
- [ ] Real-time inventory sync
- [ ] Mobile app notifications
- [ ] Performance analytics dashboard 