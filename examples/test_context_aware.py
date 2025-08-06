"""Test script to debug context-aware tools."""

import asyncio
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv
load_dotenv()

# Import and register tools
import ice_tools
from ice_tools.toolkits.ecommerce import EcommerceToolkit
EcommerceToolkit(test_mode=True, upload=False).register()

from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType

async def test_listing_agent():
    """Test the listing agent with a sample item."""
    print("Testing listing agent...")
    
    # Get the tool
    tool = registry.get_instance(NodeType.TOOL, "listing_agent")
    
    # Test item (like what would come from CSV)
    test_item = {
        "Product/Item": "Test Product",
        "Suggested Price": "$100.00",
        "Description": "Test description"
    }
    
    # Test with direct item parameter
    result = await tool.execute(item=test_item)
    print("\nDirect item parameter:")
    pprint(result)
    
    # Test with context-like structure
    context = {
        "item": test_item,
        "other_data": "ignored"
    }
    result = await tool.execute(**context)
    print("\nContext with item:")
    pprint(result)
    
    # Test with CSV row directly
    result = await tool.execute(**test_item)
    print("\nCSV row as context:")
    pprint(result)

async def test_facebook_formatter():
    """Test the facebook formatter."""
    print("\n\nTesting facebook formatter...")
    
    # Get the tool
    tool = registry.get_instance(NodeType.TOOL, "facebook_formatter")
    
    # Test enriched product
    enriched = {
        "listing_id": "TEST-123",
        "title": "Test Product",
        "description": "Test description",
        "price": 125.0
    }
    
    # Test with direct parameter
    result = await tool.execute(enriched_product=enriched)
    print("\nDirect enriched_product:")
    pprint(result)
    
    # Test with listing_agent in context
    context = {
        "listing_agent": enriched,
        "other": "data"
    }
    result = await tool.execute(**context)
    print("\nContext with listing_agent:")
    pprint(result)

async def test_aggregator():
    """Test the aggregator."""
    print("\n\nTesting aggregator...")
    
    # Get the tool
    tool = registry.get_instance(NodeType.TOOL, "aggregator")
    
    # Test results
    results = [
        {"listing_id": "TEST-1", "title": "Product 1", "price": 100},
        {"listing_id": "TEST-2", "title": "Product 2", "price": 200},
        {"error": "Failed to process"}
    ]
    
    # Test with direct parameter
    result = await tool.execute(results=results)
    print("\nDirect results:")
    pprint(result)
    
    # Test with process_loop in context
    context = {
        "process_loop": results,
        "other": "data"
    }
    result = await tool.execute(**context)
    print("\nContext with process_loop:")
    pprint(result)

async def main():
    """Run all tests."""
    await test_listing_agent()
    await test_facebook_formatter()
    await test_aggregator()

if __name__ == "__main__":
    asyncio.run(main())