# Clean Architecture Plan for iceOS

## Current Issues

1. **SDK Contains Runtime Logic**: WorkflowExecutionService, ToolService.execute()
2. **Context Split**: Some context utilities in SDK, runtime in orchestrator
3. **Service Registration Confusion**: SDK registering services it shouldn't own
4. **Leftover Components**: providers/costs.py still in SDK

## Target Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ice_api                              │
│         Pure API Gateway (Routes Only)                  │
├─────────────────────────────────────────────────────────┤
│                ice_orchestrator                         │
│    Complete Runtime (All Execution & Services)         │
├─────────────────────────────────────────────────────────┤
│                    ice_sdk                              │
│      Pure Development Kit (Tools & Builders Only)      │
├─────────────────────────────────────────────────────────┤
│                   ice_core                              │
│    Shared Foundation (Models, Protocols, Registry)     │
└─────────────────────────────────────────────────────────┘
```

## Clean Layer Responsibilities

### ice_core (Foundation)
- **Purpose**: Shared data structures and contracts
- **Contains**: 
  - Domain models (Pydantic)
  - Protocol interfaces
  - Unified registry
  - Base classes (BaseNode, BaseTool)
- **No**: Business logic, I/O, services

### ice_sdk (Developer Kit)
- **Purpose**: Tool development and workflow building
- **Contains**:
  - Tool implementations (with @tool decorator)
  - Workflow/Agent builders (config generation only)
  - Developer utilities (type coercion, etc.)
  - ServiceLocator (for accessing orchestrator services)
- **No**: Execution logic, runtime services, context management

### ice_orchestrator (Runtime Engine)
- **Purpose**: All runtime execution and services
- **Contains**:
  - Workflow execution engine
  - Tool execution service
  - Agent runtime
  - Memory subsystem
  - LLM providers and services
  - Context management (ALL of it)
  - Cost tracking
  - All service implementations
- **No**: Development utilities, builders

### ice_api (API Gateway)
- **Purpose**: HTTP/WebSocket interface only
- **Contains**:
  - FastAPI routes
  - Request/response models
  - WebSocket handlers
  - Redis event streaming
- **No**: Business logic, direct tool/agent access

## Migration Steps

### Step 1: Move Execution Services to Orchestrator
- [ ] Move `WorkflowExecutionService` → `ice_orchestrator/services/`
- [ ] Move `ToolService.execute()` logic → `ice_orchestrator/services/tool_execution_service.py`
- [ ] SDK `ToolService` becomes a simple registry/discovery facade

### Step 2: Consolidate Context Management
- [ ] Move ALL context components to orchestrator:
  - [ ] `ice_sdk/context/formatter.py` → `ice_orchestrator/context/`
  - [ ] `ice_sdk/context/types.py` → `ice_orchestrator/context/`
  - [ ] `ice_sdk/context/type_manager.py` → `ice_orchestrator/context/`

### Step 3: Clean Up SDK Services
- [ ] Remove `ice_sdk/services/workflow_service.py`
- [ ] Remove `ice_sdk/services/builder_service.py` (builders are direct, not services)
- [ ] Keep only `ServiceLocator` and `initialization.py`

### Step 4: Move Remaining Runtime Components
- [ ] Move `ice_sdk/providers/costs.py` → `ice_orchestrator/providers/`
- [ ] Move `ice_sdk/config.py` runtime config → `ice_orchestrator/config.py`

### Step 5: Simplify Service Registration
- [ ] Orchestrator registers ALL runtime services
- [ ] SDK only uses ServiceLocator to access them
- [ ] No cross-registration between layers

## Final State

### SDK Public API
```python
# Tool Development
from ice_sdk.decorators import tool
from ice_sdk.tools.base import ToolBase

# Workflow Building  
from ice_sdk.builders import WorkflowBuilder, create_agent

# Service Access
from ice_sdk.services import ServiceLocator
```

### Orchestrator Services (via ServiceLocator)
```python
# These are accessed via ServiceLocator, not imported
llm_service = ServiceLocator.get("llm_service")
workflow_service = ServiceLocator.get("workflow_service") 
tool_service = ServiceLocator.get("tool_service")
context_manager = ServiceLocator.get("context_manager")
```

## Benefits

1. **Clear Boundaries**: Each layer has a single, clear purpose
2. **No Crossover**: No execution logic in SDK, no builders in orchestrator
3. **Simple Mental Model**: SDK builds, Orchestrator runs
4. **Easy Testing**: Each layer can be tested in isolation
5. **Future-Proof**: New features clearly belong in one layer 