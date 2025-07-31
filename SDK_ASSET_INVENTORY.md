# SDK Asset Inventory: What to Preserve for Frosty

## Assets to KEEP (Move to Frosty or Keep in Place)

### 1. Tool Infrastructure ✅
**Location**: `src/ice_sdk/tools/`
**Action**: KEEP IN PLACE
- Tool base classes and decorators are perfect as-is
- The `@tool` decorator system works great
- All actual tool implementations stay where they are
- These aren't "SDK" specific - they're core to the system

### 2. ServiceLocator Pattern ✅
**Location**: `src/ice_sdk/services/locator.py`
**Action**: KEEP IN PLACE
- Critical for layer separation
- Used by tools to access orchestrator services
- Not user-facing, purely architectural

### 3. Fluent Builder Pattern 🔄
**Location**: `src/ice_sdk/builders/workflow.py`
**Action**: MIGRATE TO FROSTY
- The fluent API pattern is excellent
- Transform into `FrostyBuilder` for programmatic blueprint creation
- Change output from Workflow to Blueprint
- Example transformation:
  ```python
  # OLD (SDK)
  workflow = WorkflowBuilder().add_tool(...).build()
  
  # NEW (Frosty)
  blueprint = frosty.blueprint().add_tool(...).build()
  ```

### 4. Tool Categories & Organization ✅
**Location**: `src/ice_sdk/tools/{ai,core,db,system,web}/`
**Action**: KEEP IN PLACE
- Good organizational structure
- Clear categorization helps discovery
- Not SDK-specific

## Assets to REMOVE

### 1. WorkflowBuilder Direct Execution ❌
**Location**: `src/ice_sdk/builders/workflow.py`
**Issue**: Creates Workflow objects directly, bypassing MCP
**Action**: Remove after migrating pattern to Frosty

### 2. Agent Utilities ❌
**Location**: `src/ice_sdk/agents/`
**Issue**: Mostly empty, agents moved to orchestrator
**Action**: Delete directory

### 3. Network Service ❌
**Location**: `src/ice_sdk/services/network_service.py`
**Issue**: Just wraps NetworkCoordinator
**Action**: Users should go through Frosty instead

### 4. Registry Client ❌
**Location**: `src/ice_sdk/services/registry_client.py`
**Issue**: Internal utility, not user-facing
**Action**: Move to ice_core if needed internally

### 5. SDK Initialization ❌
**Location**: `src/ice_sdk/services/initialization.py`
**Issue**: Will be replaced by Frosty initialization
**Action**: Delete after migration

## Patterns to Preserve in Frosty

### 1. Fluent API Design
```python
# This pattern is excellent for programmatic use
builder.add_tool(...).add_llm(...).connect(...).build()
```

### 2. Memory Configuration
```python
# Simple dict-based memory config
memory={"enable_episodic": True, "enable_semantic": True}
```

### 3. Tool Discovery
```python
# The category-based organization
tools/{category}/{tool_name}.py
```

## Migration Strategy

### Phase 1: Create FrostyBuilder
1. Copy WorkflowBuilder pattern to `frosty/builder.py`
2. Change to output Blueprint instead of Workflow
3. Add validation through MCP

### Phase 2: Update Imports
```python
# Before
from ice_sdk.builders import WorkflowBuilder

# After  
from frosty import Frosty
frosty = Frosty()
builder = frosty.blueprint()
```

### Phase 3: Remove SDK Builders
1. Delete `ice_sdk/builders/`
2. Update all examples
3. Remove related tests

## What NOT to Touch

1. **Tools** - They work perfectly, just keep them
2. **ServiceLocator** - Critical infrastructure
3. **Tool decorators** - Clean and functional
4. **Tool organization** - Good categorization

## Summary

The SDK has valuable patterns (fluent API, memory config) that should move to Frosty. The actual tools and infrastructure should stay. Everything else is redundant with Frosty's vision and should be removed.

**Key Insight**: The SDK isn't bad - it's just in the wrong place. Its patterns belong in Frosty, not as a separate layer.