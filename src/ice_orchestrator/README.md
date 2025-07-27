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

## Quick Start

### Execute a Workflow
```python
from ice_orchestrator.workflow import Workflow
from ice_core.models import LLMOperatorConfig, ToolNodeConfig

# Define workflow nodes
nodes = [
    ToolNodeConfig(
        id="fetch_data",
        type="tool",
        tool_name="http_request",
        tool_args={"url": "https://api.example.com/data"},
        output_schema={"data": "dict"}
    ),
    LLMOperatorConfig(
        id="analyze",
        type="llm",
        model="gpt-4",
        prompt="Analyze this data: {data}",
        dependencies=["fetch_data"],
        output_schema={"analysis": "str"}
    )
]

# Create and execute workflow
workflow = Workflow(nodes=nodes, name="analysis_workflow")
result = await workflow.execute(context={})
print(result.node_outputs["analyze"]["analysis"])
```

### Execute an Agent
```python
from ice_orchestrator.agent import AgentNode, AgentNodeConfig
from ice_core.models.llm import LLMConfig, ModelProvider

# Configure agent with memory
config = AgentNodeConfig(
    id="assistant",
    type="agent",
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4",
        temperature=0.7
    ),
    system_prompt="You are a helpful assistant with memory.",
    tools=["web_search", "calculator"],
    enable_memory=True
)

# Execute agent
agent = AgentNode(config=config)
result = await agent.execute({
    "user_query": "What's the weather in NYC?"
})
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
├── memory/            # Memory subsystem
│   ├── base.py       # Base memory interfaces
│   ├── working.py    # Short-term working memory
│   ├── episodic.py   # Conversation history
│   ├── semantic.py   # Long-term knowledge
│   ├── procedural.py # Learned procedures
│   └── unified.py    # Unified memory interface
├── providers/         # LLM provider integrations
│   ├── llm_service.py # Main LLM service
│   └── llm_providers/ # Provider implementations
│       ├── openai_handler.py
│       ├── anthropic_handler.py
│       ├── google_gemini_handler.py
│       └── deepseek_handler.py
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

### Memory Subsystem
Comprehensive memory management:
- **Working Memory**: Short-term task context
- **Episodic Memory**: Conversation and interaction history
- **Semantic Memory**: Long-term domain knowledge
- **Procedural Memory**: Learned patterns and procedures

### LLM Services
Unified interface for multiple LLM providers:
```python
from ice_orchestrator.providers import LLMService

service = LLMService()
text, usage, error = await service.generate(
    llm_config=config,
    prompt="Your prompt here"
)
```

### Context Management
Runtime context and state management:
- `GraphContextManager`: Manages workflow execution context
- `ContextStore`: Persistent state storage
- `SessionState`: User session management

## Service Registration

The orchestrator registers its services for SDK access:
```python
# In orchestrator initialization
from ice_sdk.services import ServiceLocator

ServiceLocator.register("llm_service", llm_service_instance)
ServiceLocator.register("context_manager", context_manager_instance)
ServiceLocator.register("llm_service_impl", llm_service_instance)  # For adapter
```

## Execution Flow

1. **Workflow Creation**: Define nodes and dependencies
2. **Validation**: Static validation of node configs
3. **Graph Analysis**: Build execution levels from DAG
4. **Level Execution**: Execute nodes in parallel levels
5. **Context Flow**: Pass outputs between dependent nodes
6. **Result Collection**: Aggregate outputs and metrics

## Error Handling

Configurable failure policies:
- `HALT`: Stop on first error
- `CONTINUE_POSSIBLE`: Skip failed paths
- `ALWAYS`: Continue despite errors

## Development

```bash
make test      # Run orchestrator tests
make typecheck # Type verification
```

## Migration Notes

Recent architectural changes:
- Agent runtime moved from `ice_sdk.agents` to `ice_orchestrator.agent`
- Memory subsystem moved from `ice_sdk.memory` to `ice_orchestrator.memory`
- LLM providers moved from `ice_sdk.providers` to `ice_orchestrator.providers`
- Context management moved from `ice_sdk.context` to `ice_orchestrator.context`

## License
MIT 