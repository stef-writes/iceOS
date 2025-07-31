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

## 📐 Draft → Blueprint → Workflow Pipeline

iceOS treats workflow creation like a modern compiler:

| Stage | Artefact | Purpose | Visible To |
|-------|----------|---------|------------|
| **Design** | **Draft** (`DesignDraft`) | Lo-fi object created by Frosty or the Canvas. May include placeholders and NL comments. Often visualised as Mermaid. | Frosty & User |
| **Compile** | **Blueprint** (`ice_core.models.mcp.Blueprint`) | Fully-typed spec sent to the MCP API. Validated for schema, registry availability, cost limits, governance. | MCP API |
| **Run-time** | **Workflow** (`ice_orchestrator.workflow.Workflow`) | Concrete Python objects scheduled by the orchestrator. | Runtime only |

Validation loop:
1. Draft is converted to Blueprint.
2. POST `/api/v1/mcp/blueprints` with body `{ ..., "validate_only": true }`.
3. MCP returns `400` with structured errors OR `BlueprintAck`.
4. Frosty refines the Draft until validation passes; then submits without `validate_only` or starts a Run.

This guarantees the user gets immediate feedback in the IDE/canvas and that the orchestrator only ever sees validated graphs.

### 🔌 **Model Context Protocol (MCP) Integration**

iceOS exposes its complete orchestration capabilities through **industry-standard MCP interfaces**:

```python
# Traditional MCP servers expose simple tools:
await mcp_client.call_tool("get_weather", {"location": "NYC"})

# iceOS MCP exposes enterprise orchestration:
await mcp_client.call_tool("workflow:document_assistant", {
    "documents": ["financial_report.pdf", "market_analysis.docx"],
    "question": "What are the key investment risks?"
})
```

**MCP Capabilities Available:**
- **Tools**: Individual tools, agents, and complete workflows
- **Resources**: Blueprint templates and documentation
- **Prompts**: Pre-configured workflow creation templates
- **Transport**: HTTP JSON-RPC + stdio for Claude Desktop integration

**Endpoints:**
- `http://localhost:8000/mcp/` - HTTP JSON-RPC 2.0 endpoint
- `python src/ice_api/mcp_stdio_server.py` - stdio transport for direct integration

### 🎨 Multi-Granularity Translation

Frosty understands requests at different levels:

```python
"Parse CSV" → Tool         # Single utility
"Summarize" → Node         # Configured component  
"If error, retry" → Chain  # Connected sequence
"Daily reports" → Workflow # Complete system
```

## 🌐 Network Manifests – Multi-Workflow Coordination

A **Network manifest** lets you orchestrate *multiple* validated workflows in a single declarative file. The manifest specifies a version, a name, optional `global` config injected into every workflow’s context, and an ordered list of workflow entries.

```yaml
api_version: network.v0
name: nightly_analytics
global:
  budget_usd: 5
  memory_backend: redis://localhost:6379/3
workflows:
  - id: etl
    ref: pipelines.etl:create_workflow
  - id: train
    ref: pipelines.training:create_workflow
    after: etl
```

| Interface | How to run |
|-----------|------------|
| SDK       | `await NetworkCoordinator.execute("nightly.yml")` |
| CLI       | `ice network run nightly.yml` |
| MCP JSON-RPC | `network.execute` method |
| gRPC      | `ExecuteNetwork` on `NetworkService` |

The MVP executes workflows sequentially once their `after` prerequisites finish. Upcoming enhancements include parallel branch execution, cron scheduling, and richer telemetry aggregation.

---

## 📋 **Blueprint Execution Pattern**

iceOS follows a standardized **blueprint execution pattern** for real-world workflows. This is the recommended approach for production systems:

### **Standard Blueprint Structure**

Every use-case follows this proven pattern:

```python
#!/usr/bin/env python3
"""
🎯 [Use Case Name] - Real iceOS Blueprint Execution
===================================================

ZERO MOCKING - ALL REAL:
✅ Real [specific functionality]
✅ Real [LLM/API] integration
✅ Real agent memory storage
✅ Real workflow orchestration

Usage: python run_blueprint.py
"""

import asyncio
from ice_orchestrator.workflow import Workflow
from ice_orchestrator.execution.executor import WorkflowExecutor
from ice_core.registry import ToolRegistry, AgentRegistry

# Import real components
from .workflows import create_main_workflow
from .tools import [SpecificTools]
from .agents import [SpecificAgents]

async def run_main_blueprint() -> dict:
    """Execute real workflow with actual data."""
    
    # 1. Create workflow using builder pattern
    workflow = create_main_workflow()
    
    # 2. Register all components
    await register_components()
    
    # 3. Execute with real inputs
    executor = WorkflowExecutor()
    result = await executor.execute(workflow, real_inputs)
    
    return result

if __name__ == "__main__":
    asyncio.run(run_main_blueprint())
```

### **Workflow Builder Pattern**

Each workflow uses the **fluent WorkflowBuilder API**:

```python
def create_document_processing_workflow() -> Workflow:
    """Create document processing workflow with memory-enabled agents."""
    
    return (WorkflowBuilder("Document Processing")
        # Tools for data processing
        .add_tool("parse", "document_parser", 
                  file_path="docs/", 
                  supported_formats=["pdf", "docx", "txt"])
        
        .add_tool("chunk", "intelligent_chunker",
                  strategy="semantic",
                  chunk_size=1000,
                  overlap=100)
        
        # Agent with cognitive memory
        .add_agent("chat", "document_chat_agent",
                   tools=["semantic_search"],
                   memory={
                       "enable_episodic": True,
                       "enable_semantic": True,
                       "enable_procedural": True
                   })
        
        # Connect the pipeline
        .connect("parse", "chunk")
        .connect("chunk", "chat")
        .build()
    )
```

### **Real-World Examples**

#### **📚 Document Assistant Blueprint**
```bash
python use_cases/DocumentAssistant/run_blueprint.py
```
- **Real PDF/Word parsing** with intelligent chunking
- **Memory-powered Q&A** that learns from interactions
- **Semantic search** across document collections

#### **🛒 Facebook Marketplace Blueprint** 
```bash
python use_cases/RivaRidge/FB_Marketplace_Seller/run_blueprint.py
```
- **Real CSV inventory** processing with AI enhancement
- **Customer service agent** with episodic memory
- **Dynamic pricing** using procedural memory strategies

#### **🧠 BCI Investment Blueprint**
```bash
python use_cases/BCIInvestmentLab/run_blueprint.py
```
- **Real arXiv paper** analysis and synthesis
- **Multi-agent coordination** with recursive communication
- **All 9 node types** in sophisticated research workflow

### **Blueprint Benefits**

1. **🔧 Real Integration**: No mocking - actual APIs, files, and data
2. **📊 Observable**: Full logging and error handling
3. **🧠 Memory-Enabled**: Agents learn and improve over time
4. **⚡ Performance**: O(1) domain queries and nested optimizations
5. **🛡️ Secure**: WASM sandboxing and resource limits
6. **📋 Reproducible**: Consistent execution patterns across use-cases

## 🧠 **Cognitive Memory System**

iceOS implements a **4-tier memory architecture** that mimics human cognition, far beyond simple conversation vectorization:

### **Memory Types & Use Cases**

| Memory Type | Storage | Purpose | Example Usage |
|-------------|---------|---------|---------------|
| **🔧 Working** | In-memory dict | Active session state | `{"current_price": 450, "customer_mood": "interested"}` |
| **📚 Episodic** | Redis + timestamps | Events with outcomes | `"customer_123_negotiated_march_15" → {outcome: "sale", satisfaction: "high"}` |
| **🎯 Semantic** | Nested domains | Organized facts/knowledge | `electronics["iPhone_13"] → {market_price: 580, demand: "high"}` |
| **⚙️ Procedural** | Strategy patterns | What actually works | `"pricing_strategy_electronics" → {success_rate: 85%, steps: [...]}` |

### **Why This Architecture?**

**❌ Traditional AI frameworks:**
- Everything in one vector store
- Slow similarity search for everything  
- Can't distinguish conversation from knowledge
- No learning or strategy improvement

**✅ iceOS cognitive approach:**
- Purpose-built storage for each memory type
- O(1) domain queries vs O(n) vector search
- Clear separation of events, facts, and strategies
- Agents actually learn and improve over time

### **Developer Experience**

```python
# Agent with full cognitive memory
class CustomerServiceAgent(MemoryAgent):
    async def handle_inquiry(self, customer_id: str, inquiry: str):
        # 1. Working Memory: Current session state
        conversation_state = await self.memory.working.retrieve("current_conversation")
        
        # 2. Episodic Memory: Customer history
        history = await self.memory.episodic.search(f"customer:{customer_id}", limit=5)
        
        # 3. Semantic Memory: Product knowledge
        product_facts = await self.memory.semantic.get_facts_for_entity_in_domain(
            entity="iPhone_13", domain="electronics"
        )
        
        # 4. Procedural Memory: Best strategies
        strategy = await self.memory.procedural.get_best_strategy("customer_service")
        
        # Make intelligent decisions based on all memory types
        return self._generate_response(inquiry, history, product_facts, strategy)
```

### **Performance Benefits**

**Nested Domain Structure:**
```python
# OLD (O(n)): Search all memories
for memory in all_memories:
    if matches_domain(memory, "marketplace"): results.append(memory)

# NEW (O(1)): Direct domain access
marketplace_entities = memory.semantic.get_entities_by_domain("marketplace")
pricing_strategies = memory.procedural.get_procedures_by_category("pricing")
customer_history = memory.episodic.search(f"customer:{customer_id}")
```

**Result:** 10-100x performance improvements for large datasets.

### **Real-World Example: E-commerce Agent**

When a customer asks about iPhone pricing:

1. **Episodic**: "This customer negotiated before, accepts 10% discounts, last purchase was $420"
2. **Semantic**: "iPhone 13 market price: $580, competitor range: $550-600, demand: high"  
3. **Procedural**: "Use 'electronics_negotiation' strategy - 85% success rate for this category"
4. **Working**: "Current conversation: customer interested, mentioned budget of $550"

The agent uses **all four memory types** to make an informed decision, not just similarity search on past conversations.

---

## ✨ **iceOS Syntax Simplicity Principle**

iceOS follows a **"Simple Things Simple, Complex Things Possible"** philosophy that dramatically improves developer experience:

### **The Principle**

**❌ Traditional AI Frameworks:**
```python
# Complex, verbose, error-prone configuration
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, Tool

# 20+ lines of boilerplate for simple task
memory = ConversationBufferMemory(memory_key="chat_history")
prompt = PromptTemplate(
    input_variables=["chat_history", "input"],
    template="Previous conversation: {chat_history}\nHuman: {input}\nAI:"
)
llm = OpenAI(temperature=0.7, model_name="gpt-4")
chain = LLMChain(llm=llm, prompt=prompt, memory=memory)
tools = [Tool(name="Calculator", func=lambda x: eval(x), description="...")]
agent = initialize_agent(tools, llm, agent="conversational-react-description", memory=memory)
```

**✅ iceOS Simplified:**
```python
# Intuitive, fluent, powerful
workflow = (WorkflowBuilder("Customer Chat")
    .add_agent("chat", "customer_service_agent",
               tools=["calculator", "order_lookup"],
               memory={"enable_episodic": True})
    .build()
)

result = await WorkflowExecutor().execute(workflow, {"user_input": "..."})
```

### **Simplicity Achievements**

| Complexity Level | Traditional Approach | iceOS Approach | Improvement |
|------------------|---------------------|----------------|-------------|
| **Simple Tasks** | 20+ lines boilerplate | 3-5 fluent lines | **80% reduction** |
| **Tool Integration** | Manual wiring/config | Auto-registration with `@tool` | **95% reduction** |
| **Memory Management** | Complex setup/retrieval | `memory={"enable_episodic": True}` | **90% reduction** |
| **Workflow Building** | Imperative step-by-step | Declarative fluent API | **70% reduction** |
| **Error Handling** | Manual try/catch everywhere | Built-in with observability | **85% reduction** |

### **Developer Experience Wins**

#### **1. Fluent Workflow Building**
```python
# Express intent directly - no configuration objects
workflow = (WorkflowBuilder("Sales Analysis")
    .add_tool("read_csv", "csv_reader", file="sales.csv")
    .add_llm("analyze", "gpt-4", "Find key insights: {{read_csv.output}}")
    .add_agent("presenter", "presentation_agent", tools=["chart_maker"])
    .connect("read_csv", "analyze")
    .connect("analyze", "presenter")
    .build()
)
```

#### **2. Auto-Registration Magic**
```python
# No manual registration needed
@tool  # Automatically available as "weather_checker"
class WeatherChecker(ToolBase):
    async def _execute_impl(self, city: str) -> dict:
        return {"weather": f"Sunny in {city}"}

# Use immediately in any workflow
.add_tool("weather", "weather_checker", city="San Francisco")
```

#### **3. Memory-First Design**
```python
# Cognitive memory in one line
.add_agent("customer_service", "service_agent",
           memory={
               "enable_episodic": True,   # Customer history
               "enable_semantic": True,   # Product knowledge  
               "enable_procedural": True  # Best practices
           })
```

#### **4. Real-World Blueprint Pattern**
```python
# Production-ready execution pattern
#!/usr/bin/env python3
"""Real Document Processing - ZERO MOCKING"""

async def run_blueprint():
    workflow = create_document_processing_workflow()
    result = await WorkflowExecutor().execute(workflow, real_inputs)
    return result

if __name__ == "__main__":
    asyncio.run(run_blueprint())
```

### **Why This Matters**

**Faster Development:**
- **Minutes to prototype** instead of hours
- **Copy-paste examples** that actually work
- **Progressive complexity** - start simple, add sophistication

**Fewer Bugs:**
- **Type-safe** with Pydantic models everywhere
- **Clear abstractions** reduce configuration errors
- **Built-in validation** catches problems early

**Better Maintainability:**
- **Self-documenting** fluent APIs
- **Consistent patterns** across all use-cases
- **Clean separation** of concerns

**The result:** Developers can focus on **business logic** instead of **framework complexity**.

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
  
- **Memory Subsystem** (via `ice_core.memory`): Comprehensive memory
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
  - **NEW: Recursive flows** with controlled cycles and convergence detection
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

2. **Memory Subsystem** → ✅ Moved to Core  
   - All memory implementations in `ice_core/memory/`
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
from ice_core.memory import WorkingMemory
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
from ice_core.memory import UnifiedMemory

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

## Recursive Flows Architecture

iceOS now supports **recursive workflows** - a breakthrough capability that enables agent conversations to continue until convergence, putting iceOS on par with LangGraph while maintaining all enterprise features.

### Key Components

- **RecursiveNodeConfig**: Pydantic model with convergence conditions and safety limits
- **Enhanced Cycle Detection**: Smart analysis allowing controlled cycles for recursive nodes
- **Recursive Executor**: Context-preserving execution with convergence detection
- **WorkflowBuilder Integration**: Simple `add_recursive()` API for building recursive workflows

### Architecture Benefits

```python
# Before: DAG-only (like traditional systems)
User → Agent A → Agent B → End

# After: Recursive flows (like LangGraph + enterprise features)
User → Agent A ↔ Agent B → Convergence → End
             ↑_____↓ (until agreement)
```

### Safety & Enterprise Features

- **Convergence Detection**: Expressions evaluated safely (e.g., `agreement_reached == True`)
- **Safety Limits**: Max iterations prevent infinite loops
- **Context Preservation**: Enterprise-grade memory management across iterations
- **Full Observability**: Complete metrics, tracing, and error handling
- **Type Safety**: Strict Pydantic validation and mypy compliance

### Use Cases

- **Agent Negotiations**: Multi-turn bargaining until agreement
- **Consensus Building**: Team agents working toward shared decisions
- **Iterative Refinement**: Continuous improvement loops
- **Complex Problem Solving**: Back-and-forth reasoning between specialists

## Performance Considerations

- **Lazy Loading**: Services loaded on first access
- **Connection Pooling**: LLM providers share connections
- **Memory Management**: Configurable memory limits
- **Parallel Execution**: Level-based DAG processing
- **Recursive Optimization**: Efficient context reuse in recursive flows

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

## The 9 Clean Node Types

iceOS uses 9 distinct, non-overlapping node types for building workflows:

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

8. **Recursive Node** (`type: "recursive"`)
   - **Purpose**: Agent conversations until convergence with controlled cycles
   - **Use Cases**: Multi-turn negotiations, iterative refinement, consensus building
   - **Example**: `convergence_condition: "agreement_reached == True"`

### Composition Node

9. **Workflow Node** (`type: "workflow"`)
   - **Purpose**: Embed sub-workflows
   - **Use Cases**: Reusable components, modular design
   - **Example**: `workflow_ref: "checkout_process"`

### Key Design Principles

- **No Overlaps**: Each node type has a single, clear purpose
- **No Auto-Upgrades**: What you specify is what executes
- **Complete Coverage**: All use cases are covered by exactly one node type
- **Explicit Over Implicit**: Users must choose the right node type 