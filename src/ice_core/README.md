# ice_core - Foundation Layer

## Vision Context

This is the foundation for the **3-tier iceOS architecture**:
- 🧊 **Frosty** (Interpreter) → Natural language to blueprints
- 📋 **MCP API** (Compiler) → Blueprint validation & optimization ← *Core models used here*
- ⚙️ **Orchestrator** (Runtime) → Deterministic execution

## Why This Layer Exists

`ice_core` provides the **pure domain models and shared infrastructure** that all other layers build upon:

1. **Blueprint Models** (`models/node_models.py`)
   - Config classes like `LLMOperatorConfig`, `ToolNodeConfig`
   - These represent the "design time" form created by Frosty
   - Support incremental canvas construction

2. **Protocol Interfaces** (`protocols/`)
   - Define contracts between layers
   - Enable testing with simple stubs
   - Keep layers loosely coupled

3. **Unified Registry** (`unified_registry.py`)
   - 🚀 **Enhanced with nested `NodeType` structure** for O(1) access patterns
   - Central registry for all components (nodes, tools, agents, chains)
   - Shared by all layers to maintain component catalog
   - Enables dynamic discovery and instantiation
   - **Performance**: Type-based organization eliminates string parsing and enables instant filtering

4. **Pure Utilities** (`utils/`)
   - No side effects or I/O
   - Shared by all layers above

## Multi-Granularity Support

The models support Frosty's 4-level translation:
- **Tool**: `ToolNodeConfig` - Single utilities
- **Node**: `LLMOperatorConfig` - Configured components  
- **Chain**: `AgentNodeConfig` - Multi-step sequences
- **Workflow**: `WorkflowConfig` - Complete systems

## Key Design Decisions

- **Pydantic Everywhere**: Type safety and validation
- **No External Dependencies**: Pure Python domain layer
- **Separate Config from Runtime**: Enables progressive validation
- **Central Registry**: Single source of truth for all components

See `docs/Looking_Forward/iceos-comprehensive_vision_roadmap.md` for future vision and research frontiers. 