"""Check if loop executor is registered."""

from ice_core.unified_registry import registry, get_executor

# List all registered executors
print("Registered executors:")
print(registry._executors.keys())

# Try to get loop executor
try:
    loop_exec = get_executor("loop")
    print(f"\nLoop executor found: {loop_exec}")
except Exception as e:
    print(f"\nError getting loop executor: {e}")

# Check what happens when we import unified
print("\nImporting unified executors...")
import ice_orchestrator.execution.executors.unified

# Check again
print("\nAfter import:")
print("Registered executors:", registry._executors.keys())

try:
    loop_exec = get_executor("loop")
    print(f"Loop executor now available: {loop_exec}")
except Exception as e:
    print(f"Still error: {e}")