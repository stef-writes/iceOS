"""Test individual tools to debug issues."""

import asyncio
from pathlib import Path

# Import our tools
from tools.read_inventory_csv import ReadInventoryCSVTool


async def test_csv_tool():
    """Test the CSV reading tool directly."""
    
    print("🧪 Testing CSV tool...")
    
    tool = ReadInventoryCSVTool()
    
    # Test with our inventory file
    csv_file = Path(__file__).parent / "inventory.csv"
    
    try:
        result = await tool._execute_impl(csv_file=str(csv_file))
        print(f"✅ CSV tool result: {result}")
        return result
    except Exception as e:
        print(f"❌ CSV tool failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Test our tools individually."""
    
    print("🔬 TESTING INDIVIDUAL TOOLS")
    print("="*50)
    
    # Test CSV tool
    csv_result = await test_csv_tool()
    
    if csv_result and csv_result.get("success"):
        print(f"📄 CSV loaded {csv_result.get('items_imported', 0)} items")
        
        # Show first item as example
        items = csv_result.get("clean_items", [])
        if items:
            print(f"📋 First item: {items[0]}")
    else:
        print("❌ CSV test failed")


if __name__ == "__main__":
    asyncio.run(main()) 