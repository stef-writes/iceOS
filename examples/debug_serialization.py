"""Debug script to find JSON serialization issue."""
import asyncio
import json
from pathlib import Path

from ice_core.models.node_models import ToolNodeConfig
from ice_orchestrator.workflow import Workflow

# Ensure tools are loaded
import ice_tools


async def main():
    """Run minimal workflow to debug serialization."""
    
    # Single CSV loader node only
    csv_path = Path("src/ice_tools/ecommerce/Supply Yard - Overflow Items - Sheet1.csv").resolve()
    
    load_csv = ToolNodeConfig(
        id="load_csv",
        name="Load CSV",
        type="tool",
        tool_name="csv_loader",
        tool_args={"path": str(csv_path), "delimiter": ","},
        dependencies=[]
    )
    
    # Create workflow with just one node
    wf = Workflow(
        nodes=[load_csv],
        name="Debug Workflow",
        version="1.0"
    )
    
    print("Executing single node workflow...")
    
    # Patch json.dumps to see what's being serialized
    original_dumps = json.dumps
    def debug_dumps(obj, **kwargs):
        try:
            return original_dumps(obj, **kwargs)
        except TypeError as e:
            print(f"\n❌ JSON serialization failed!")
            print(f"Error: {e}")
            print(f"Object type: {type(obj)}")
            print(f"Object repr: {repr(obj)[:200]}...")
            import traceback
            traceback.print_stack()
            raise
    
    json.dumps = debug_dumps
    
    try:
        result = await wf.execute()
        print("✅ Workflow completed!")
        
        if hasattr(result, 'output'):
            print(f"\nOutput: {result.output}")
        
    except Exception as e:
        print(f"\n❌ Execution failed: {type(e).__name__}: {e}")
        
    finally:
        json.dumps = original_dumps


if __name__ == "__main__":
    asyncio.run(main())