#!/usr/bin/env python3
"""Demo script to showcase new HTTP API client and activity simulator features."""

import asyncio
from tools.facebook_api_client import FacebookAPIClientTool
from tools.activity_simulator import ActivitySimulatorTool


async def demo_new_features():
    print('🌐 TESTING REAL HTTP API CALLS')
    print('=' * 50)
    
    # Test real HTTP API calls
    api_client = FacebookAPIClientTool()
    
    # Get customer messages with real HTTP
    print('📱 Fetching customer messages via real HTTP...')
    messages_result = await api_client.execute(action='get_messages')
    print(f'✅ HTTP Status: {messages_result.get("http_status")}')
    print(f'📧 Messages retrieved: {messages_result.get("total_messages")}')
    for msg in messages_result.get('messages', [])[:2]:
        print(f'   💬 {msg["customer_id"]}: {msg["inquiry"][:60]}...')
    
    # Create listing with real HTTP POST
    print(f'\n📡 Creating listing via real HTTP POST...')
    test_listing = [{
        'sku': 'DEMO-001',
        'title': 'Premium Dell Laptop',
        'description': 'Excellent condition laptop for sale',
        'price': 450.00,
        'category': 'electronics'
    }]
    
    create_result = await api_client.execute(
        action='create_listing',
        listings=test_listing
    )
    print(f'✅ HTTP Calls made: {create_result.get("http_calls_made")}')
    print(f'📦 Listings created: {create_result.get("successful_listings")}')
    print(f'🌐 API Endpoint: {create_result.get("api_endpoint")}')
    
    print(f'\n\n🎭 TESTING MARKETPLACE ACTIVITY SIMULATION')
    print('=' * 50)
    
    # Test marketplace activity simulation  
    simulator = ActivitySimulatorTool()
    
    # Mock listings for simulation
    mock_listings = [
        {'sku': 'LAPTOP-001', 'title': 'Dell XPS Laptop', 'name': 'Dell XPS', 'price': 325},
        {'sku': 'TOOLS-001', 'title': 'Cordless Drill Set', 'name': 'Drill Set', 'price': 65},
        {'sku': 'BIKE-001', 'title': 'Mountain Bike', 'name': 'Mountain Bike', 'price': 180}
    ]
    
    # Simulate customer messages
    print('💬 Simulating customer inquiries...')
    messages_sim = await simulator.execute(
        activity_type='customer_messages',
        duration_minutes=2,
        listings=mock_listings
    )
    print(f'📱 Messages generated: {messages_sim.get("total_messages")}')
    print(f'⚡ Message rate: {messages_sim.get("message_rate"):.1f} per minute')
    for msg in messages_sim.get('messages', [])[:3]:
        print(f'   📩 {msg["customer_name"]}: {msg["inquiry"][:50]}...')
    
    # Simulate sales events
    print(f'\n💰 Simulating sales transactions...')
    sales_sim = await simulator.execute(
        activity_type='sales_events',
        duration_minutes=2,
        listings=mock_listings.copy()
    )
    print(f'🎉 Sales completed: {sales_sim.get("total_sales")}')
    print(f'💵 Total revenue: ${sales_sim.get("total_revenue", 0):.2f}')
    for sale in sales_sim.get('sales', []):
        print(f'   💸 {sale["item_title"]}: ${sale["listing_price"]} → ${sale["sale_price"]} ({sale["reason"]})')
    
    # Simulate complete ecosystem
    print(f'\n🎪 Simulating complete marketplace ecosystem...')
    ecosystem_sim = await simulator.execute(
        activity_type='all',
        duration_minutes=3,
        listings=mock_listings.copy()
    )
    summary = ecosystem_sim.get('summary', {})
    print(f'🎯 ECOSYSTEM RESULTS:')
    print(f'   📱 Customer messages: {summary.get("total_messages")}')
    print(f'   💰 Sales: {summary.get("total_sales")} (${summary.get("total_revenue", 0):.2f})')
    print(f'   📈 Market events: {summary.get("market_events")}')
    
    print(f'\n✨ NEW FEATURES DEMO COMPLETE!')


if __name__ == "__main__":
    asyncio.run(demo_new_features()) 