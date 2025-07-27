# iceOS - AI Workflow Orchestration System

A clean, layered architecture for building and executing AI workflows with strict separation of concerns.

## 🎯 Vision

Transform natural language requests into executable AI workflows:

```
User: "Analyze sales data and generate insights"
    ↓
Workflow: Tool → LLM → Agent → Results
```

## 🏗️ Architecture Overview

iceOS follows a strict 4-layer architecture where each layer has a specific purpose:

```
┌─────────────────────────────────────────────────────────┐
│                    ice_api                              │
│            HTTP/WebSocket Gateway                       │
├─────────────────────────────────────────────────────────┤
│                ice_orchestrator                         │
│     Runtime Engine (Agents, Memory, LLM, Context)      │
├─────────────────────────────────────────────────────────┤
│                    ice_sdk                              │
│      Developer SDK (Tools, Builders, Services)         │
├─────────────────────────────────────────────────────────┤
│                   ice_core                              │
│         Foundation (Models, Protocols, Registry)        │
└─────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

- **ice_core**: Shared models, protocols, and unified registry
- **ice_sdk**: Tool development, workflow builders, service locator
- **ice_orchestrator**: Runtime execution, agents, memory, LLM services
- **ice_api**: External HTTP/WebSocket interfaces

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/iceos.git
cd iceos

# Install dependencies with Poetry
poetry install

# Run tests
make test

# Start the API server
uvicorn ice_api.main:app --reload
```

### Build Your First Tool

```python
from ice_sdk.decorators import tool
from ice_sdk.tools.base import ToolBase

@tool(name="data_analyzer")
class DataAnalyzer(ToolBase):
    """Analyze data and return insights."""
    
    async def _execute_impl(self, **kwargs):
        data = kwargs["data"]
        # Your analysis logic here
        return {"insights": ["insight1", "insight2"]}
```

### Create a Workflow

```python
from ice_sdk.builders import WorkflowBuilder

# Build workflow
builder = WorkflowBuilder("analysis_workflow")

# Add nodes
builder.add_tool("fetch", tool_name="http_request", url="https://api.example.com")
builder.add_tool("analyze", tool_name="data_analyzer")

# Connect nodes
builder.connect("fetch", "analyze")

# Execute via API
workflow_config = builder.build()
```

### Execute an Agent

```python
from ice_sdk.builders import create_agent

# Configure agent
agent_config = create_agent(
    name="assistant",
    model="gpt-4",
    tools=["web_search", "calculator"],
    system_prompt="You are a helpful assistant"
)

# Agent execution happens in orchestrator runtime
```

## 📋 Recent Architectural Migration

We've completed a major architectural refactoring to improve separation of concerns:

### What Changed

1. **Runtime → Orchestrator**: Agent execution, memory subsystem, LLM providers, and context management moved from SDK to orchestrator
2. **Registry → Core**: Unified registry moved from SDK to core for shared access
3. **Service Pattern**: SDK now uses ServiceLocator to access orchestrator services
4. **Clear Boundaries**: Each layer now has distinct responsibilities

### Migration Guide

```python
# Old imports (incorrect)
from ice_sdk.agents import AgentNode
from ice_sdk.memory import WorkingMemory
from ice_sdk.providers.llm_service import LLMService

# New imports (correct)
from ice_orchestrator.agent import AgentNode
from ice_orchestrator.memory import WorkingMemory
from ice_sdk.services import ServiceLocator

# Access LLM service via ServiceLocator
llm_service = ServiceLocator.get("llm_service")
```

## 🛠️ Key Components

### Tools (SDK)
- CSV, JSON, file operations
- AI-powered tools (insights, summarization)
- Web tools (HTTP, search, webhooks)
- Database optimization tools

### Agents (Orchestrator)
- Autonomous agents with tool access
- Memory-enabled agents
- Custom reasoning loops

### Memory (Orchestrator)
- Working memory (short-term)
- Episodic memory (conversations)
- Semantic memory (knowledge)
- Procedural memory (learned patterns)

### LLM Services (Orchestrator)
- OpenAI, Anthropic, Gemini, DeepSeek
- Unified interface
- Cost tracking

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - Detailed architecture documentation
- [API Reference](src/ice_api/README.md) - API endpoints and usage
- [SDK Guide](src/ice_sdk/README.md) - Tool development guide
- [Orchestrator Details](src/ice_orchestrator/README.md) - Runtime engine documentation
- [Core Models](src/ice_core/README.md) - Foundation layer reference

## 🧪 Testing

```bash
# Run all tests
make test

# Type checking
make typecheck

# Linting
make lint

# Run specific test suites
pytest tests/unit/ice_sdk
pytest tests/integration/ice_orchestrator
```

## 🔒 Security & Best Practices

- **Layer Isolation**: Each layer has specific access patterns
- **Service Locator**: Controlled access to runtime services
- **Input Validation**: Pydantic models at all boundaries
- **Tool Sandboxing**: Limited permissions for tool execution

## 🤝 Contributing

1. Follow the layer architecture - no cross-layer imports
2. Use ServiceLocator for accessing orchestrator services from SDK
3. Write tests for new components
4. Update documentation for API changes
5. Run `make test` before submitting PRs

## 📄 License

MIT - See [LICENSE](LICENSE) file for details.

## 🎯 Roadmap

- [ ] Plugin system for dynamic tool loading
- [ ] Distributed workflow execution
- [ ] Advanced monitoring and observability
- [ ] Visual workflow editor
- [ ] Workflow versioning and rollback

---

Built with ❤️ for clean architecture and AI workflow orchestration. 