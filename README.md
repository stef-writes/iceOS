# iceOS v1(A)

> *"Give every distributed team a shared canvas where natural-language ideas become governance-ready AI workflows in seconds."*

---

## What is iceOS?

iceOS is an **alpha-stage AI workflow runtime** designed for:

* **Zero-code design** – blueprints created from natural language via Frosty or the canvas editor
* **Governed execution** – budget & safety guardrails enforced at runtime
* **Team memory** – every run is traceable, costed and searchable

The runtime is powered by the **Workflow** engine - a spatial computing DAG executor with NetworkX-powered graph intelligence - and exposed through the **Model Context Protocol (MCP)** HTTP API.

### 🎯 Workflow Engine: The Spatial Computing Powerhouse

At the heart of iceOS lies the **Workflow** engine - designed from the ground up for both traditional workflow execution and future spatial computing experiences:

**🧠 Graph Intelligence**
- NetworkX-powered dependency analysis and optimization
- Real-time bottleneck detection and parallelization suggestions
- Pattern recognition for workflow refactoring opportunities

**🎨 Canvas-Ready Architecture**  
- Spatial layout hints for visual programming interfaces
- Scope-based organization with contextual AI assistance
- Real-time collaboration with cursor tracking and shared state

**🤖 Frosty AI Integration**
- Contextual suggestions based on graph position and flow
- Intelligent node recommendations using dependency analysis
- AI-powered optimization and debugging assistance

**⚡ Advanced Execution**
- Level-based parallel execution with intelligent scheduling
- Event streaming for real-time canvas updates
- Incremental execution and checkpoint recovery

---

## 🚀 Quick Start

### Install

```bash
# Using Poetry (recommended)
poetry install --with dev

# Or with pip
pip install -e ".[dev]"
```

📚 **[Full Setup Guide](docs/SETUP_GUIDE.md)** - Detailed instructions for getting started

### Run the Comprehensive Demo

```bash
# Start the server
make dev

# In another terminal, run the demo
python examples/comprehensive_demo.py
```

The demo showcases:
- 📝 Incremental blueprint construction (Frosty-style)
- 💰 Cost estimation before execution
- 🚀 Real-time event streaming
- 🔍 Debug information and monitoring
- 🔗 Nested workflow composition

### Run the Marketplace Workflow Demo

```bash
# In another terminal (with server running)
python examples/marketplace_workflow_demo.py
```

This advanced demo demonstrates:
- 🏪 Real-world workflow: selling surplus inventory via Facebook Marketplace
- 💸 Budget-conscious AI usage ($5 budget limit)
- 🛠️ Custom tools: InventoryAnalyzer, ListingGenerator, InquiryResponder
- 🤖 Smart agents: ListingAgent with template optimization
- 💬 Automated buyer inquiry handling
- 📊 Performance tracking and cost optimization

### Running the API

```bash
# Start the FastAPI server
make dev

# Or run directly
uvicorn ice_api.main:app --reload
```

The API will be available at http://localhost:8000 with interactive docs at http://localhost:8000/docs.

---

## Architecture

iceOS follows a clean, layered architecture with strict boundaries:

```
┌─────────────────────────────────────┐
│         ice_api (HTTP/WS)          │
├─────────────────────────────────────┤
│    ice_orchestrator (Engine)       │
├─────────────────────────────────────┤
│        ice_sdk (Tools/SDK)         │
├─────────────────────────────────────┤
│      ice_core (Domain/Models)      │
└─────────────────────────────────────┘
```

For detailed architecture documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Key Features

- **Clean Layer Boundaries**: Each layer only imports from layers below
- **Service Locator Pattern**: Dependency injection without tight coupling  
- **Protocol-Based Interfaces**: Testable contracts between layers
- **Async-First Design**: Non-blocking I/O throughout
- **Type Safety**: Pydantic models and mypy strict mode

---

## Development

### Running Tests

```bash
# Run full test suite
make test

# Run specific test categories
pytest tests/unit/        # Unit tests
pytest tests/integration/ # Integration tests
pytest tests/smoke/       # Smoke tests
```

### Type Checking

```bash
# Run mypy in strict mode
make type

# Or directly
mypy --strict src/
```

### Code Quality

The project enforces:
- ✅ Type hints on all functions [[memory:3930965]]
- ✅ Mypy strict mode compliance
- ✅ 90%+ test coverage on changed lines
- ✅ Clean layer architecture with no violations

---

## Using the SDK

### Building Workflows

```python
from ice_sdk import WorkflowBuilder, WorkflowExecutionService

# Create a workflow
builder = WorkflowBuilder("my_workflow")
builder.add_llm("summarize", model="gpt-4", prompt="Summarize: {{text}}")
builder.add_tool("fetch", tool_name="http_request", url="{{url}}")
builder.connect("fetch", "summarize")

# Execute it
result = await WorkflowExecutionService.execute_workflow_builder(
    builder,
    inputs={"url": "https://example.com"}
)
```

### Creating Tools

```python
from ice_sdk import ToolBase
from typing import Dict, Any

class MyTool(ToolBase):
    name = "my_tool"
    description = "Does something useful"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        # Tool implementation
        result = await do_something(kwargs["input"])
        return {"output": result}
```

---

## API Endpoints

### Direct Execution (NEW)
Quick testing and experimentation without creating full workflows:

- `POST /api/v1/tools/{tool_name}` - Execute a single tool
- `POST /api/v1/agents/{agent_name}` - Execute a single agent  
- `POST /api/v1/units/{unit_name}` - Execute a single unit
- `POST /api/v1/chains/{chain_name}` - Execute a single chain

### Model Context Protocol (MCP)

- `POST /api/v1/mcp/blueprints` - Register workflow blueprints
- `POST /api/v1/mcp/runs` - Execute workflows
- `GET /api/v1/mcp/runs/{run_id}` - Get execution results
- `GET /api/v1/mcp/runs/{run_id}/events` - Stream execution events

### Discovery

- `GET /api/v1/tools` - List available tools
- `GET /api/v1/executors` - List available executors
- `GET /health` - Health check endpoint

---

## Contributing

1. Fork and create a feature branch
2. Follow the architecture guidelines in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
3. Ensure all tests pass (`make test`)
4. Submit a PR with clear description

### Development Rules

1. **Layer Boundaries**: Never import from higher layers
2. **Side Effects**: Only in Tool implementations
3. **Type Safety**: All code must pass mypy strict
4. **Documentation**: All public APIs need docstrings

---

## Roadmap

| Milestone | ETA | Status |
|-----------|-----|--------|
| **Alpha Runtime** | Q3 2024 | ✅ Complete |
| **Canvas Editor** | Q4 2024 | 🚧 In Progress |
| **Frosty Integration** | Q1 2025 | 📋 Planned |
| **Public Beta** | Q2 2025 | 📋 Planned |

---

## License

[Apache-2.0](LICENSE) 