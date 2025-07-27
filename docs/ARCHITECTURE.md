# iceOS Architecture

## Quick Start Guide

### 🎯 The Vision: Natural Language → Executable Workflows

```
User: "Analyze my sales data weekly and email insights"
   ↓
Frosty: Creates blueprint with nodes and connections
   ↓  
MCP: Validates, optimizes, estimates cost ($0.12/run)
   ↓
Orchestrator: Executes with retries, monitoring, guarantees
```

### 🏗️ Three-Tier Architecture

| Tier | Purpose | Key Components | Why It Exists |
|------|---------|----------------|---------------|
| **Frosty** | Interpreter | NL→Blueprint translator | Users think in natural language |
| **MCP API** | Compiler | Validation, optimization | Catch errors before execution |
| **Orchestrator** | Runtime | DAG execution engine | Deterministic, observable runs |

### 🎨 Multi-Granularity Translation

Frosty understands requests at different levels:

```python
"Parse CSV" → Tool         # Single utility
"Summarize" → Node         # Configured component  
"If error, retry" → Chain  # Connected sequence
"Daily reports" → Workflow # Complete system
```

---

## Overview

iceOS is a clean, layered AI workflow orchestration system designed with clear separation of concerns and strict layer boundaries. The architecture follows Domain-Driven Design principles with a focus on maintainability and extensibility.

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ice_api                              │
│  (HTTP/WebSocket API Layer - FastAPI)                      │
├─────────────────────────────────────────────────────────────┤
│                    ice_orchestrator                         │
│  (Runtime Engine - Agents, Memory, LLM, Context)           │
├─────────────────────────────────────────────────────────────┤
│                        ice_sdk                              │
│  (Developer SDK - Tools, Builders, ServiceLocator)         │
├─────────────────────────────────────────────────────────────┤
│                       ice_core                              │
│  (Foundation - Models, Protocols, Registry)                │
└─────────────────────────────────────────────────────────────┘
```

### Layer Rules

1. **Dependency Direction**: Each layer can only import from layers below it
2. **No Cross-Layer Imports**: Direct imports across layers are forbidden
3. **Service Pattern**: SDK uses ServiceLocator for orchestrator services
4. **Side Effects**: External I/O only in Tool implementations

## Core Components by Layer

### ice_core (Foundation Layer)

Pure domain layer with shared infrastructure:

- **Models** (`models/`): Pydantic data models for all domain objects
  - `NodeConfig` hierarchy: `ToolNodeConfig`, `LLMOperatorConfig`, `AgentNodeConfig`
  - `LLMConfig`, `ModelProvider` for LLM configuration
  - `NodeExecutionResult`, `NodeMetadata` for execution tracking
  
- **Protocols** (`protocols/`): Python Protocol interfaces
  - `INode`, `ITool`, `IWorkflow` for core abstractions
  - `IEmbedder`, `IVectorStore` for ML operations
  - `NodeProtocol`, `ToolProtocol` for runtime contracts
  
- **Unified Registry** (`unified_registry.py`): Central component registry
  - Single source of truth for all components
  - Handles tools, agents, chains, executors
  - Shared across all layers
  
- **Base Classes** (`base_node.py`, `base_tool.py`): Abstract foundations
  - Common behavior for nodes and tools
  - Validation and execution contracts

### ice_sdk (Developer SDK)

Developer-facing tools and utilities:

- **Tools** (`tools/`): Categorized tool implementations
  - **Base** (`base.py`): `ToolBase` base class (simplified 2-level hierarchy)
  - **Core** (`core/`): CSV, JSON, file operations
  - **AI** (`ai/`): Insights, summarizer (using ServiceLocator for LLM)
  - **System** (`system/`): Sleep, jinja templates, computer control
  - **Web** (`web/`): HTTP, search, webhooks
  - **DB** (`db/`): Database optimization tools
  - **Marketplace** (`marketplace/`): Domain-specific tools
  
- **Builders** (`builders/`): Fluent APIs for construction
  - `WorkflowBuilder`: Build workflows programmatically
  - `AgentBuilder`: Configure agents (config only, not runtime)
  
- **Services** (`services/`): Service layer
  - `ServiceLocator`: Dependency injection pattern
  - `initialization.py`: SDK service setup
  - `llm_adapter.py`: Adapter for LLM service access
  
- **Context Utilities** (`context/`): SDK-specific context helpers
  - `ContextFormatter`: Format context for display
  - `ToolContext`: Context type for tools
  - `ContextTypeManager`: Manage context types
  
- **Decorators** (`decorators.py`): Simple @tool decorator
  - Auto-registration with unified registry
  - Simplified focus on registration only
  
- **Utils** (`utils/`): Developer utilities
  - Type coercion, error handling, retry logic

### ice_orchestrator (Runtime Engine)

Complete runtime execution environment:

- **Agent Runtime** (`agent/`): Full agent implementation
  - `AgentNode`, `AgentNodeConfig`: Base agent with tool loop
  - `MemoryAgent`: Agent with integrated memory
  - `AgentExecutor`: Tool coordination and LLM reasoning
  
- **Memory Subsystem** (`memory/`): Comprehensive memory
  - `WorkingMemory`: Short-term task context
  - `EpisodicMemory`: Conversation history
  - `SemanticMemory`: Long-term knowledge
  - `ProceduralMemory`: Learned procedures
  - `UnifiedMemory`: Integrated memory interface
  
- **LLM Providers** (`providers/`): Model integrations
  - `LLMService`: Unified LLM interface
  - Provider handlers: OpenAI, Anthropic, Gemini, DeepSeek
  
- **Context Management** (`context/`): Runtime state
  - `GraphContextManager`: Workflow execution context
  - `ContextStore`: Persistent state storage
  - `SessionState`: User session tracking
  
- **LLM Operators** (`llm/operators/`): Specialized processors
  - `InsightsOperator`: Generate actionable insights
  - `SummarizerOperator`: Text summarization
  - `LineItemGenerator`: Structured data generation
  
- **Workflow Engine** (`workflow.py`): Core orchestration
  - DAG-based execution with level parallelism
  - Error handling and retry policies
  - Context propagation between nodes
  
- **Node Executors** (`nodes/`): Type-specific execution
  - `ToolNode`, `LLMNode`, `AgentNode` bridges
  - `ConditionNode`, `LoopNode`, `ParallelNode`

### ice_api (API Layer)

External HTTP/WebSocket interfaces:

- **MCP Router** (`api/mcp.py`): Model Context Protocol
  - Blueprint registration and persistence
  - Workflow execution endpoints
  - Event streaming via Redis
  
- **Direct Execution** (`api/direct_execution.py`): Quick endpoints
  - `/tools/{name}`, `/agents/{name}` for single execution
  - Discovery endpoints for component listing
  
- **WebSocket Gateway** (`ws_gateway.py`): Real-time updates
  - Live workflow execution events
  - Progress tracking

## Service Architecture

### ServiceLocator Pattern

The SDK accesses orchestrator services without direct imports:

```python
# In SDK tool implementation
from ice_sdk.services import ServiceLocator

llm_service = ServiceLocator.get("llm_service")
result = await llm_service.generate(config, prompt)

# In orchestrator initialization
ServiceLocator.register("llm_service", LLMService())
ServiceLocator.register("context_manager", GraphContextManager())
```

### Registered Services

1. **llm_service**: LLM provider access
2. **llm_service_impl**: Internal LLM service (for adapter)
3. **context_manager**: Workflow context management
4. **tool_service**: Tool discovery and execution
5. **workflow_service**: Workflow execution service

## Data Flow Example

```
1. API receives request → Creates workflow config
                    ↓
2. Orchestrator validates → Builds execution graph
                    ↓
3. Executes nodes in levels → Tools use ServiceLocator
                    ↓
4. Agent nodes run loops → Access memory & LLM
                    ↓
5. Results flow back → Events stream via Redis
```

## Key Design Changes (Latest Migration)

### ✅ COMPLETED: Clean Architecture Migration

The architectural migration has been successfully completed:

1. **Agent Runtime** → ✅ Moved to Orchestrator
   - AgentNode, MemoryAgent, AgentExecutor now in `ice_orchestrator/agent/`
   - SDK only provides builders and utilities

2. **Memory Subsystem** → ✅ Moved to Orchestrator  
   - All memory implementations in `ice_orchestrator/memory/`
   - Working, episodic, semantic, procedural memory

3. **LLM Services** → ✅ Moved to Orchestrator
   - LLMService and all providers in `ice_orchestrator/providers/`
   - SDK accesses via ServiceLocator

4. **Context Management** → ✅ Consolidated in Orchestrator
   - ALL context components in `ice_orchestrator/context/`
   - No more split between layers

5. **Unified Registry** → ✅ Moved to Core
   - Now properly in `ice_core/unified_registry.py`
   - Shared foundation for all layers

6. **Service Pattern** → ✅ Clean ServiceLocator Implementation
   - SDK only uses ServiceLocator to access orchestrator services
   - No direct imports between layers
   - All runtime services registered by orchestrator

7. **Tool Hierarchy** → ✅ Simplified to 2 Levels
   - Removed `AITool` and `DataTool` category base classes
   - All tools inherit directly from `ToolBase`
   - Simplified `@tool` decorator focused on registration

### Current State

The architecture now achieves complete separation of concerns:

- **ice_core**: Pure data structures and contracts
- **ice_sdk**: Pure development kit (tools and builders only)
- **ice_orchestrator**: ALL runtime execution and services
- **ice_api**: Pure HTTP/WebSocket gateway

No layer violations remain. Each layer has a single, clear purpose.

## Tool Architecture (Simplified)

### Clean 2-Level Hierarchy

```python
ice_core.base_tool.ToolBase    # Abstract base with execute() contract
├── CSVTool                    # Direct inheritance 
├── InsightsTool               # Direct inheritance
├── ComputerTool               # Direct inheritance
└── All other tools            # All inherit directly from ToolBase
```

### Benefits of Simplified Tool Hierarchy

1. **One Pattern**: All tools follow the same inheritance pattern
2. **No Confusion**: No choice paralysis about which base class to use
3. **Faster Development**: Less boilerplate, clearer examples
4. **Easier Maintenance**: Single base class to update
5. **Category Metadata**: Use simple attributes instead of inheritance

### Tool Development Pattern

```python
from ice_sdk.decorators import tool
from ice_sdk.tools.base import ToolBase

@tool  # Auto-registers with snake_case name
class DataProcessorTool(ToolBase):
    name = "data_processor"
    description = "Process data files"
    category = "core"          # Simple metadata
    requires_llm = False       # Simple metadata
    
    async def _execute_impl(self, **kwargs):
        # Tool implementation
        return {"processed": True}
```

## Migration Guide

For existing code:

```python
# Old (incorrect)
from ice_sdk.agents import AgentNode
from ice_sdk.memory import WorkingMemory
from ice_sdk.providers.llm_service import LLMService
from ice_sdk.tools.ai.base import AITool
from ice_sdk.tools.core.base import DataTool

# New (correct)
from ice_orchestrator.agent import AgentNode
from ice_orchestrator.memory import WorkingMemory
from ice_sdk.services import ServiceLocator
from ice_sdk.tools.base import ToolBase  # All tools inherit from ToolBase

llm_service = ServiceLocator.get("llm_service")
```

## Testing Strategy

### Layer-Specific Tests
- **Core**: Pure unit tests, no I/O
- **SDK**: Tool tests with mocked services
- **Orchestrator**: Integration tests with real components
- **API**: End-to-end tests with full stack

### Boundary Tests
- Verify no illegal imports between layers
- Check ServiceLocator usage in SDK
- Validate all cross-layer contracts

## Development Guidelines

### Adding a New Tool (SDK)

```python
from ice_sdk.decorators import tool
from ice_sdk.tools.base import ToolBase
from ice_sdk.services import ServiceLocator

@tool  # Auto-registers as "my_tool" 
class MyTool(ToolBase):
    name = "my_tool"
    description = "Does something useful"
    
    async def _execute_impl(self, **kwargs):
        # Access orchestrator services if needed
        llm_service = ServiceLocator.get("llm_service")
        return {"result": "success"}
```

### Adding a New Agent (Orchestrator)

```python
from ice_orchestrator.agent import AgentNode, AgentNodeConfig
from ice_orchestrator.memory import UnifiedMemory

class CustomAgent(AgentNode):
    def __init__(self, config: AgentNodeConfig):
        super().__init__(config)
        self.memory = UnifiedMemory(config.memory_config)
```

### Adding a New Service

1. Define interface in `ice_core/protocols/`
2. Implement in appropriate layer (usually orchestrator)
3. Register in orchestrator initialization
4. Document in ServiceLocator registry
5. Access via ServiceLocator in SDK

## Performance Considerations

- **Lazy Loading**: Services loaded on first access
- **Connection Pooling**: LLM providers share connections
- **Memory Management**: Configurable memory limits
- **Parallel Execution**: Level-based DAG processing

## Security Considerations

- **Layer Isolation**: Each layer has specific responsibilities
- **Service Access**: Controlled through ServiceLocator
- **Selective Sandboxing**: User code runs in WASM; tools/agents use direct execution
- **Input Validation**: Pydantic models at every boundary

## Future Enhancements

1. **Plugin System**: Dynamic tool/agent loading
2. **Distributed Execution**: Multi-node orchestration
3. **Advanced Monitoring**: Full observability stack
4. **Workflow Versioning**: Blueprint version control
5. **Visual Editor**: Canvas-based design

## Conclusion

The iceOS architecture provides clear separation of concerns:
- **Core**: Shared models and infrastructure
- **SDK**: Developer tools and utilities
- **Orchestrator**: Complete runtime environment
- **API**: External interfaces

This separation enables independent evolution of each layer while maintaining clean contracts through protocols and service patterns. 

## The 8 Clean Node Types

iceOS uses 8 distinct, non-overlapping node types for building workflows:

### Execution Nodes

1. **Tool Node** (`type: "tool"`)
   - **Purpose**: Execute a single tool without LLM
   - **Use Cases**: CSV parsing, API calls, data transformations
   - **Example**: `tool_name: "csv_reader"`

2. **LLM Node** (`type: "llm"`)
   - **Purpose**: Pure text generation, NO tools allowed
   - **Use Cases**: Summarization, translation, text analysis
   - **Example**: `prompt: "Summarize this article"`

3. **Agent Node** (`type: "agent"`)
   - **Purpose**: LLM + Tools + Memory for multi-turn reasoning
   - **Use Cases**: Customer support, research tasks, debugging
   - **Example**: `package: "ice_sdk.agents.support"`

4. **Code Node** (`type: "code"`)
   - **Purpose**: Direct code execution
   - **Use Cases**: Custom logic, data transformations
   - **Example**: `code: "return sum(data['values'])"`

### Control Flow Nodes

5. **Condition Node** (`type: "condition"`)
   - **Purpose**: If/else branching based on expressions
   - **Use Cases**: Conditional logic, routing
   - **Example**: `expression: "result > 100"`

6. **Loop Node** (`type: "loop"`)
   - **Purpose**: Iterate over collections
   - **Use Cases**: Batch processing, data aggregation
   - **Example**: `items_source: "products"`

7. **Parallel Node** (`type: "parallel"`)
   - **Purpose**: Concurrent execution of branches
   - **Use Cases**: Performance optimization, independent operations
   - **Example**: `branches: [["node1", "node2"], ["node3"]]`

### Composition Node

8. **Workflow Node** (`type: "workflow"`)
   - **Purpose**: Embed sub-workflows
   - **Use Cases**: Reusable components, modular design
   - **Example**: `workflow_ref: "checkout_process"`

### Key Design Principles

- **No Overlaps**: Each node type has a single, clear purpose
- **No Auto-Upgrades**: What you specify is what executes
- **Complete Coverage**: All use cases are covered by exactly one node type
- **Explicit Over Implicit**: Users must choose the right node type 