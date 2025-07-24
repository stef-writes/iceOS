# ice_sdk – Spatial Computing Developer SDK

## Purpose
`ice_sdk` is the primary public surface for _developers_ building spatial computing experiences on iceOS.
It provides:
* Typed **Node & Tool** abstractions with spatial intelligence
* **Workflow** integration for canvas-ready execution  
* **Frosty AI** integration points for contextual assistance
* A **Provider** layer (LLM, vector, embedding) with enhanced analytics
* High-level **Agent** helpers with memory and collaboration features
* **Workflow builders** for programmatic DAG construction with spatial layout hints
* **Graph analyzers** for NetworkX-powered intelligence and optimization
* Unified **Registry** for all components with backward compatibility

> **Spatial Computing Ready**: All SDK components are designed for both traditional execution and future canvas-based experiences.

> Rule: Nothing inside `ice_sdk.*` may import from higher layers (ice_api, ice_orchestrator)

## Quick-start: Spatial Computing Workflows
```python
from ice_sdk.builders.workflow import WorkflowBuilder
from ice_core.models import LLMConfig, ModelProvider

# Build a workflow with correct field names
builder = WorkflowBuilder("spatial_demo")

# Add tool node (uses tool_name, not tool_ref)
builder.add_tool(
    "fetch", 
    tool_name="http_request",  # Correct field name
    url="https://example.com"
)

# Add LLM nodes with rich LLMConfig
builder.add_llm(
    "analyze", 
    model="gpt-4",
    prompt="Analyze this content: {content}",  # NOT prompt_template
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000
    )
)

builder.add_llm(
    "summarize",
    model="gpt-3.5-turbo", 
    prompt="Summarize: {analysis}",  # Single braces for Python format
    temperature=0.5  # Node-level override
)

# Connect nodes
builder.connect("fetch", "analyze")
builder.connect("analyze", "summarize")
```

### Agent Example (with rich LLMConfig)
```python
from ice_core.models import AgentNodeConfig, LLMConfig, ModelProvider

# Create agent with rich configuration
agent_config = AgentNodeConfig(
    id="researcher",
    type="agent", 
    package="ice_sdk.agents.research.ResearchAgent",  # NOT agent_ref
    max_iterations=5,  # New field to prevent loops
    llm_config=LLMConfig(  # Agents now have LLM config!
        provider=ModelProvider.ANTHROPIC,
        model="claude-3-opus",
        temperature=0.7,
        max_tokens=4000
    ),
    tools=[],  # List of ToolConfig objects
    memory={"type": "conversation"}
)
```

## Package Layout (Cleaned)

```
ice_sdk/
├── agents/             # Agent implementations (AgentNode)
├── builders/           # Workflow construction APIs
├── context/            # Execution context management
├── llm/                # LLM operators (summarizer, insights, etc)
├── providers/          # External service adapters (OpenAI, Anthropic, etc)
├── services/           # Service facades and initialization
├── tools/              # Tool implementations (system, web, db)
├── utils/              # SDK-specific utilities
├── config.py           # Runtime configuration
├── decorators.py       # @tool decorator
├── exceptions.py       # SDK exceptions
├── plugin_discovery.py # Dynamic plugin loading
└── unified_registry.py # Single registry for all components
```

### Removed/Consolidated
- ~~nodes/~~ - Moved to ice_orchestrator
- ~~models/~~ - Use ice_core.models directly
- ~~interfaces/~~ - Use ice_core.protocols
- ~~protocols/~~ - Use ice_core.protocols
- ~~events/~~ - Unused
- ~~dsl/~~ - Unused
- ~~core/~~ - Moved to ice_core
- ~~registry/~~ - Consolidated into unified_registry.py

## Layer Boundaries
* Depends _only_ on `ice_core`
* Exposes **validate()** on every Node/Tool
* External I/O lives strictly inside `tools/` or `providers/`
* All cross-layer communication via ServiceLocator

## Key Components

### Unified Registry
Single source of truth for all registrations:
```python
from ice_sdk.unified_registry import registry, register_node

# Register a node executor
@register_node("custom")
async def custom_executor(chain, cfg, ctx):
    ...

# Register tools, agents, chains
registry.register_tool("my_tool", MyTool())
registry.register_agent("my_agent", MyAgent())
```

### Service Initialization
Clean initialization without layer violations:
```python
from ice_sdk.services.initialization import initialize_services
initialize_services()  # Sets up all SDK and orchestrator services
```

## Development
```bash
make test   # unit + integration tests
make type   # mypy --strict
```

## License
MIT 