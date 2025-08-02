# ice_orchestrator – Workflow Execution Engine

## Overview

`ice_orchestrator` is the runtime execution engine for iceOS workflows. It orchestrates the execution of nodes, manages runtime dependencies, and provides all runtime services including agents, memory, LLM providers, and context management.

**🎯 Core Responsibilities**
* **Workflow Execution** – DAG-based workflow orchestration with parallel execution
* **Agent Runtime** – Execution of autonomous agents with tool access and memory
* **Memory Management** – Working, episodic, semantic, and procedural memory systems
* **LLM Services** – Provider integrations (OpenAI, Anthropic, Gemini, DeepSeek)
* **Context Management** – Runtime context, state persistence, and data flow
* **Node Execution** – Built-in executors for all node types (tool, LLM, agent, etc.)
* **Error Handling** – Resilient execution with configurable failure policies

## Quick Start (Local)
```bash
# Run tests to ensure orchestrator is healthy
make test
# Execute a demo blueprint locally
poetry run ice run-blueprint examples/hello_world.json
```

## Architecture

```
┌─────────────────┐          ┌─────────────────┐
│  Workflow API   │          │   Agent API     │
└────────┬────────┘          └────────┬────────┘
         │                            │
         ▼                            ▼
┌─────────────────────────────────────────────┐
│           Execution Engine                  │
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │ Executors   │  │ Context Management   │ │
│  └─────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────┘
         │                            │
         ▼                            ▼
┌─────────────────┐          ┌─────────────────┐
│ Memory Subsystem│          │  LLM Providers  │
└─────────────────┘          └─────────────────┘
```

## Package Structure

```
ice_orchestrator/
├── agent/              # Agent runtime implementation
│   ├── base.py        # AgentNode, AgentNodeConfig
│   ├── memory.py      # MemoryAgent implementation
│   ├── executor.py    # AgentExecutor for tool coordination
│   └── utils.py       # Agent utilities
├── (memory provided by ice_core.memory)

├── providers/         # Budget enforcement utilities
├── (LLM service in `ice_core.llm.service`)
├── (Provider handlers in `ice_core.llm.providers/`)
├── context/           # Runtime context management
│   ├── async_manager.py    # GraphContextManager
│   ├── manager.py          # GraphContext
│   ├── store.py            # Context storage
│   ├── session_state.py    # Session management
│   └── memory.py           # Memory adapter
├── llm/               # LLM operators
│   └── operators/     # Specialized operators
│       ├── insights.py
│       ├── summarizer.py
│       └── line_item_generator.py
├── execution/         # Execution engine
│   ├── executor.py    # Main executor
│   ├── executors/     # Node type executors
│   ├── agent_factory.py # Agent creation
│   └── metrics.py     # Execution metrics
├── nodes/             # Node implementations
│   ├── tool.py       # Tool node executor
│   ├── llm.py        # LLM node executor
│   ├── agent.py      # Agent node bridge
│   └── workflow.py   # Nested workflow node
├── workflow.py        # Main workflow class
└── base_workflow.py   # Base workflow abstractions
```

## Key Components

### Agent Runtime
The complete agent implementation including:
- `AgentNode`: Base agent with tool execution loop
- `MemoryAgent`: Agent with integrated memory subsystems
- `AgentExecutor`: Coordinates tool calls and LLM reasoning

### Memory Subsystem (powered by ice_core.memory)

- **Working Memory**: Short-term task context
- **Episodic Memory**: Conversation and interaction history  
- **Semantic Memory**: Long-term domain knowledge with **O(1) domain queries**
- **Procedural Memory**: Learned patterns with **O(1) category targeting**



➡️ **[Memory Architecture Details](../ice_core/memory/README.md)**

### LLM Services
Unified interface for multiple LLM providers:
```python
from ice_core.llm.service import LLMService

service = LLMService()
text, usage, error = await service.generate(
    llm_config=config,
    prompt="Your prompt here"
)
```

### Context Management

- `GraphContextManager`: Manages workflow execution context with **O(1) node access by type**
- `ContextStore`: Persistent state storage
- `SessionState`: User session management



### Execution Metrics


**Performance Tracking by Node Type:**
- **📊 Type-based Metrics**: `get_metrics_by_node_type(NodeType.AGENT)` - instant filtering
- **💰 Cost Tracking**: `get_total_cost_by_node_type(NodeType.TOOL)` - budget monitoring
- **📈 Performance Summary**: `get_performance_summary()` - dashboard-ready breakdown
- **⚡ Token Analytics**: `get_total_tokens_by_node_type()` - usage monitoring

**Workflow State Analytics:**
- **🎯 Success Rates**: `get_success_rate_by_node_type()` - performance tracking by type
- **📋 Results Organization**: `get_results_by_node_type()` - O(1) access to execution results
- **🔍 Performance Breakdown**: Complete analytics with success rates, costs, and tokens by node type

## Security & Sandboxing Strategy

### Selective WASM Sandboxing 🔒

iceOS uses a **selective sandboxing approach** that balances security with functionality:

**🟢 Direct Execution (Trusted Components)**
- **Tool Nodes**: Need file I/O, network access, library imports
- **Agent Nodes**: Require full Python capabilities for reasoning
- **LLM Nodes**: Need network access for API calls
- **Orchestration Logic**: Core system functionality

**🔒 WASM Sandboxed (Untrusted Content)**
- **Code Nodes**: User-provided Python code with unknown security risk
- **Dynamic Expressions**: Condition evaluations from untrusted source

## Execution Flow

1. **Workflow Creation**: Define nodes and dependencies
2. **Validation**: Static validation of node configs
3. **Graph Analysis**: Build execution levels from DAG
4. **Level Execution**: Execute nodes in parallel levels
5. **Context Flow**: Pass outputs between dependent nodes
6. **Result Collection**: Aggregate outputs and metrics

## License
MIT 