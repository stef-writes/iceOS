# Facebook Marketplace Seller Automation

A complete workflow automation system for managing Facebook Marketplace listings, from inventory analysis to customer communication.

## Project Structure

```
FB-Marketplace-Seller/
├── FBMSeller.py           # Main workflow orchestrator
├── __init__.py            # Package initialization
├── agents/                # Intelligent agents for complex tasks
│   ├── __init__.py
│   ├── marketplace_agent.py      # Listing creation and optimization
│   └── customer_service_agent.py # Customer interaction handling
├── nodes/                 # Workflow nodes for specific tasks
│   ├── __init__.py
│   ├── inventory_analyzer/       # Analyze inventory for listing eligibility
│   ├── pricing_optimizer/        # Optimize pricing based on market data
│   ├── listing_creator/          # Create marketplace listings
│   ├── image_processor/          # Process and enhance product images
│   ├── conversation_manager/     # Manage buyer conversations
│   ├── order_handler/            # Handle orders and transactions
│   └── metrics_tracker/          # Track performance metrics
├── tools/                 # Reusable tools for specific operations
│   ├── __init__.py
│   ├── marketplace/              # Facebook Marketplace API tools
│   ├── inventory/                # Inventory management tools
│   ├── analytics/                # Analytics and reporting tools
│   └── communication/            # Messaging and notification tools
├── workflows/             # Pre-defined workflow templates
├── config/                # Configuration files
└── tests/                 # Unit and integration tests
```

## Quick Start

```python
from use_cases.RivaRidge.FB_Marketplace_Seller import FBMSeller

# Initialize the workflow
seller = FBMSeller(config={
    "marketplace": "facebook",
    "location": "Seattle, WA",
    "category": "Electronics"
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

1. **Inventory Analysis** - Filter items suitable for listing
2. **Pricing Optimization** - Determine competitive pricing
3. **Image Processing** - Enhance product images
4. **Listing Creation** - Generate and post listings
5. **Conversation Management** - Monitor and respond to inquiries
6. **Order Handling** - Process sales and coordinate pickup
7. **Metrics Tracking** - Monitor performance and optimize

## Key Components

### Nodes
Each node represents a discrete step in the workflow:
- **InventoryAnalyzerNode**: Filters inventory based on condition and value
- **PricingOptimizerNode**: Uses market data to set competitive prices
- **ListingCreatorNode**: Generates listing content and posts to marketplace
- **ImageProcessorNode**: Enhances images for better presentation
- **ConversationManagerNode**: Handles buyer inquiries
- **OrderHandlerNode**: Manages the sales process
- **MetricsTrackerNode**: Tracks KPIs and generates reports

### Tools
Reusable tools that nodes and agents can leverage:
- **FacebookAPITool**: Direct interface with Facebook Marketplace
- **PriceResearchTool**: Analyze market prices for similar items
- **ImageEnhancerTool**: AI-powered image enhancement
- **MessageParserTool**: Parse and understand buyer messages

### Agents
Intelligent agents that orchestrate complex multi-step processes:
- **MarketplaceAgent**: Creates optimized listings using AI
- **CustomerServiceAgent**: Handles customer interactions professionally

## Configuration

The system can be configured via the `config` parameter:

```python
config = {
    "marketplace": "facebook",
    "location": "Seattle, WA",
    "categories": ["Electronics", "Home & Garden"],
    "pricing_strategy": "competitive",
    "auto_respond": True,
    "response_delay_minutes": 5,
    "min_item_value": 10.0,
    "acceptable_conditions": ["New", "Like New", "Good"]
}
```

## Development

To add new components:

1. **New Node**: Create a folder in `nodes/` with the node implementation
2. **New Tool**: Add to appropriate subfolder in `tools/`
3. **New Agent**: Add to `agents/` directory
4. Update the respective `__init__.py` files to export your component

## Testing

Run tests with:
```bash
python -m pytest tests/
```

## Future Enhancements

- [ ] Multi-marketplace support (OfferUp, Craigslist, etc.)
- [ ] Advanced pricing algorithms
- [ ] Automated negotiation handling
- [ ] Inventory sync with external systems
- [ ] Mobile app notifications
- [ ] Performance analytics dashboard 