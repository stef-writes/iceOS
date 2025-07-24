# ice_sdk – Spatial Computing Developer SDK

## Purpose
`ice_sdk` is the primary public surface for _developers_ building spatial computing experiences on iceOS.
It provides:
* Typed **Node & Tool** abstractions with spatial intelligence
* **iceEngine** integration for canvas-ready workflows  
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
from ice_sdk import WorkflowBuilder, WorkflowExecutionService
from ice_orchestrator.workflow import iceEngine

# Build a workflow with spatial intelligence
builder = WorkflowBuilder("spatial_demo")
builder.add_tool("fetch", tool_name="http_request", url="https://example.com")
builder.add_llm("analyze", model="gpt-4", prompt="Analyze this content: {{content}}")
builder.add_llm("summarize", model="gpt-3.5-turbo", prompt="Summarize: {{analysis}}")
builder.connect("fetch", "analyze")
builder.connect("analyze", "summarize")

# Execute with iceEngine spatial features
result = await WorkflowExecutionService.execute_workflow_builder(
    builder, 
    inputs={"doc_url": "https://example.com"},
    enable_spatial_features=True,
    enable_frosty_integration=True
)

# Get spatial intelligence and optimization suggestions
engine = result.engine
layout_hints = engine.get_spatial_layout_hints()  # For canvas visualization
metrics = engine.get_enhanced_metrics()          # Graph analysis
suggestions = engine.get_optimization_suggestions()  # AI-powered improvements
```

### Frosty Integration Example
```python
from ice_sdk.context.graph_analyzer import GraphAnalyzer

# Get AI suggestions for next nodes
suggestions = engine.suggest_next_nodes_enhanced("analyze")
for suggestion in suggestions:
    print(f"💡 {suggestion['reason']}: {suggestion['type']}")

# Apply Frosty suggestion
result = engine.apply_frosty_suggestion(suggestion_id="opt_123")
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