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

### ⚠️ Yes, We Have Duplicate Class Names (It's Intentional!)

| Class Name | Location | Purpose |
|------------|----------|---------|
| `LLMOperatorConfig` | `ice_core.models` | Blueprint for workflows |
| `LLMOperatorConfig` | `ice_sdk.llm.operators` | Internal SDK config |

**Simple Rule**: Building workflows? Use `ice_core`. Writing SDK internals? Use `ice_sdk`.

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
│  (Workflow Execution Engine - DAG Processing)              │
├─────────────────────────────────────────────────────────────┤
│                        ice_sdk                              │
│  (Developer SDK - Tools, Agents, Services)                 │
├─────────────────────────────────────────────────────────────┤
│                       ice_core                              │
│  (Domain Models, Protocols, Base Classes)                  │
└─────────────────────────────────────────────────────────────┘
```

### Layer Rules

1. **Dependency Direction**: Each layer can only import from layers below it
2. **No Cross-Layer Imports**: Direct imports across layers are forbidden
3. **Service Interfaces**: All cross-layer communication goes through service interfaces
4. **Side Effects**: External I/O only in Tool implementations (ice_sdk/tools)

## Core Components

### ice_core (Foundation Layer)

Pure domain layer with no external dependencies:

- **Models** (`models/`): Pydantic data models for all domain objects
  - `NodeConfig`, `NodeExecutionResult`, `NodeMetadata`
  - `LLMConfig`, `MessageTemplate`
  - `BaseNode`, `ToolBase` abstract base classes
  
- **Protocols** (`protocols/`): Python Protocol interfaces
  - `INode`, `ITool`, `IWorkflow`
  - `IEmbedder`, `IVectorStore`
  - `WorkflowLike`, `ScriptChainLike`
  
- **Utils** (`utils/`): Pure utility functions
  - Hashing, coercion, validation helpers
  - No I/O or side effects

### ice_sdk (Developer SDK) - CLEANED & REORGANIZED

User-facing APIs and implementations with a streamlined structure:

- **Tools** (`tools/`): Categorized by purpose and cost model
  - **Core** (`core/`): Free, fast data manipulation (unified CSV, JSON, file operations)
  - **AI** (`ai/`): LLM-powered tools with cost tracking (insights, summarizer, generators)
  - **System** (`system/`): OS and utility operations (sleep, compute, templates)
  - **Integration** (`integration/`):
    - Web (`web/`): HTTP requests, webhooks, search
    - DB (`db/`): Query optimization, schema validation
    - Cloud (`cloud/`): Future cloud service integrations
  - **Domain** (`domain/`): Business-specific tools (marketplace, analytics)
  
- **Agents** (`agents/`): LLM-powered decision makers
  - `AgentNode`: Configurable agent with tool access
  
- **Services** (`services/`): Service facades and locators
  - `ServiceLocator`: Dependency injection registry
  - `WorkflowExecutionService`: Clean workflow execution API
  - `initialization.py`: Centralized service setup
  
- **Builders** (`builders/`): Fluent APIs for workflow construction
  - `WorkflowBuilder`: Programmatic workflow creation

- **Context** (`context/`): Execution context management
  - `GraphContextManager`: State management during execution

- **LLM** (`llm/`): LLM operators for text processing
  - `SummarizerOperator`, `InsightsOperator`, etc.

- **Providers** (`providers/`): External service integrations
  - OpenAI, Anthropic, Google Gemini, DeepSeek handlers

- **Utils** (`utils/`): SDK-specific utilities
  - Error handling, retry logic, token counting

- **Unified Registry** (`unified_registry.py`): Single registry for all components
  - Replaces previous scattered registry modules
  - Handles tools, agents, chains, executors in one place

### ice_orchestrator (Execution Engine)

Workflow execution and coordination:

- **Workflow** (`workflow.py`): Core DAG executor
  - Level-based execution with proper error handling
  - Context propagation between nodes
  
- **Nodes** (`nodes/`): Concrete node implementations
  - `ToolNode`, `LLMNode`, `AgentNode`
  - `ConditionNode`, `LoopNode`, `ParallelNode`
  
- **Services** (`services/`): Orchestration services
  - `WorkflowService`: IWorkflowService implementation
  
- **Validation** (`validation/`): Pre-flight checks
  - Schema validation, safety checks, cycle detection

### ice_api (API Layer)

External HTTP/WebSocket interfaces:

- **MCP Router** (`api/mcp.py`): Model Context Protocol endpoints
  - Blueprint registration and management
  - Workflow execution via HTTP
  
- **WebSocket Gateway** (`ws_gateway.py`): Real-time event streaming
  - Live workflow execution updates
  
- **Main App** (`main.py`): FastAPI application
  - Clean initialization using SDK services
  - No direct orchestrator imports

## Service Architecture

### ServiceLocator Pattern

The `ServiceLocator` provides dependency injection without tight coupling:

```python
# Registration (during initialization)
ServiceLocator.register("workflow_service", WorkflowService())

# Usage (anywhere in the code)
workflow_service = ServiceLocator.get("workflow_service")
```

### Common Services

1. **workflow_service**: IWorkflowService for workflow execution
2. **workflow_proto**: Workflow class for SDK usage
3. **tool_service**: ToolService for tool discovery/execution
4. **context_manager**: GraphContextManager for state management
5. **llm_service**: LLMService for model interactions

## Initialization Flow

1. **API Startup** (`ice_api/main.py`):
   ```python
   from ice_sdk.services.initialization import initialize_services
   initialize_services()  # Sets up all layers
   ```

2. **SDK Initialization** (`ice_sdk/services/initialization.py`):
   - Checks for orchestrator availability
   - Registers SDK services
   - Calls orchestrator initialization if present

3. **Orchestrator Setup** (`ice_orchestrator/__init__.py`):
   - Registers workflow service
   - Registers workflow prototype

## Key Design Decisions

### 1. Single Unified Registry
- All registrations in `ice_sdk/unified_registry.py`
- No scattered registry modules
- Backward compatibility through wrapper classes

### 2. Clean SDK Structure
- Removed 12 unnecessary directories
- Consolidated from ~20 subdirectories to 8 essential ones
- No more compatibility shims or re-exports

### 3. Protocol-Based Interfaces
- Use Python Protocols for contracts
- Allows testing with simple stubs

### 4. Pydantic Everywhere
- All data structures are Pydantic models
- Automatic validation and serialization

### 5. Async-First
- All I/O operations are async
- Proper context managers for resources

### 6. Intentional Duplicate Class Names
- **This is by design, not confusion!**
- Blueprint layer (`ice_core.models`) has `LLMOperatorConfig`, `AgentNodeConfig` for workflow definitions
- SDK layer (`ice_sdk`) has duplicate names for internal runtime implementations
- Supports progressive canvas workflow building and clean execution separation
- See [CONFIG_CLARIFICATION.md](./CONFIG_CLARIFICATION.md) for detailed explanation

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock external dependencies
- Focus on business logic

### Integration Tests
- Test layer interactions
- Use real services where possible
- Validate end-to-end flows

### Smoke Tests
- Basic functionality checks
- Ensure system can start
- Validate critical paths

## Development Guidelines

### Adding a New Tool

**Option 1: Enhanced @tool Decorator (Recommended)**
```python
from ice_sdk.decorators import tool
from ice_sdk.tools.core.base import DataTool  # or AITool

@tool(name="my_tool", auto_generate_tests=True)
class MyTool(DataTool):
    """Tool description."""
    async def _execute_impl(self, **kwargs):
        return {"result": "success"}
```

**Option 2: CLI Scaffolding**
```bash
ice scaffold tool --interactive
# Follow prompts for name, category, inputs/outputs
```

**Option 3: Traditional Method**
1. Choose appropriate category: `core/`, `ai/`, `system/`, `web/`, `db/`
2. Inherit from category base class (`DataTool`, `AITool`, etc.)
3. Implement `_execute_impl()` method
4. Tool auto-registers via decorator
5. Tests can be auto-generated

### Adding a New Node Type

1. Create node class in `ice_orchestrator/nodes/`
2. Inherit from appropriate base class
3. Register executor if needed
4. Add validation logic
5. Write integration tests

### Adding a New Service

1. Define protocol in `ice_core/protocols/`
2. Implement in appropriate layer
3. Register in initialization
4. Add to ServiceLocator docs
5. Write usage examples

## Recent Improvements

### SDK Cleanup (Latest)
- Deleted unused directories: nodes/, events/, dsl/, interfaces/, protocols/, core/, models/
- Consolidated all registry functionality into `unified_registry.py`
- Updated all imports to use `ice_core.models` directly
- Removed compatibility layers and shims
- Cleaner, more maintainable structure

### Tool Reorganization & Enhancement (Latest)
- **Category-based structure**: Tools now organized by purpose (core, ai, system, etc.)
- **Unified tools**: CSV read/write combined into single `csv` tool with actions
- **Enhanced @tool decorator**: Auto-registration, schema generation, test creation
- **CLI scaffolding**: Interactive tool generation with `ice scaffold tool`
- **Cost awareness**: AI tools clearly separated with cost estimation
- **Base classes**: `DataTool` for free operations, `AITool` for LLM-powered tools

## Future Enhancements

1. **Plugin System**: Dynamic tool/node discovery
2. **Distributed Execution**: Multi-node workflow processing
3. **Advanced Monitoring**: OpenTelemetry integration
4. **Workflow Versioning**: Blueprint version management
5. **Visual Editor**: Canvas-based workflow design

## Conclusion

The iceOS architecture provides a clean, maintainable foundation for AI workflow orchestration. By following strict layer boundaries and using well-defined interfaces, the system remains flexible while preventing architectural drift. The recent SDK cleanup has significantly improved maintainability by reducing complexity and removing unnecessary abstractions. 