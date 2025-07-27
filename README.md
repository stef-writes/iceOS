# iceOS - AI Workflow Orchestration System

A clean, layered architecture for building and executing AI workflows with enterprise-grade security and strict separation of concerns.

## 🎯 Vision

Transform natural language requests into executable AI workflows:

```
User: "Analyze sales data and generate insights"
    ↓
Workflow: Tool → LLM → Agent → Results
```

## 🛡️ **Security-First Design**

User code execution runs in **WASM sandboxes** with resource limits:
- CPU/memory monitoring and enforcement
- Import restrictions and network isolation  
- Timeout protection and audit logging
- OpenTelemetry observability integration

## 🏗️ Architecture Overview

iceOS follows a strict 4-layer architecture where each layer has a specific purpose:

```
┌─────────────────────────────────────────────────────────┐
│                    ice_api                              │
│       HTTP/WebSocket Gateway + MCP Blueprint API       │
├─────────────────────────────────────────────────────────┤
│                ice_orchestrator                         │
│   Runtime Engine (Agents, Memory, LLM, WASM Security)  │
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
- **ice_orchestrator**: Runtime execution, agents, memory, LLM services, WASM security
- **ice_api**: External HTTP/WebSocket interfaces, MCP blueprint API

### 🏆 **Enterprise Features**

- **🔐 WASM Sandboxing**: User code execution in secure WebAssembly containers
- **🧠 Unified Memory**: Working/Episodic/Semantic/Procedural agent memory
- **⚡ Plugin System**: Protocol-based with 20+ production tools
- **📊 Observability**: OpenTelemetry tracing, structured logging, metrics
- **🔄 Reusable Components**: Enterprise patterns for tool/agent sharing

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

@tool  # Auto-registers as "data_analyzer"
class DataAnalyzer(ToolBase):
    """Analyze data and return insights."""
    
    name = "data_analyzer"
    description = "Analyzes data and returns insights"
    
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

## 🎯 Featured Demo: Facebook Marketplace Automation

**Experience the full power of iceOS with our production-ready marketplace automation system:**

```bash
cd use-cases/RivaRidge/FB_Marketplace_Seller
python enhanced_blueprint_demo.py
```

**What makes this demo exceptional:**
- 🤖 **Real LLM Integration**: 40+ actual GPT-4o API calls
- 🌐 **Live HTTP Requests**: Real network calls to external APIs  
- 🧠 **Memory-Enabled Agents**: Customer service and pricing optimization
- 🎭 **Ecosystem Simulation**: Realistic customer interactions and market dynamics
- ⚡ **Two Execution Patterns**: MCP Blueprint (enterprise) + SDK WorkflowBuilder (developer)

**Results**: Complete marketplace automation from CSV inventory → AI enhancement → publishing → customer service → dynamic pricing, with comprehensive testing and verification.

➡️ **[View Complete Demo Documentation](use-cases/RivaRidge/FB_Marketplace_Seller/README.md)**

## 📋 Recent Architectural Migration

We've completed major architectural refactoring with significant improvements:

### What Changed

1. **Runtime → Orchestrator**: Agent execution, memory subsystem, LLM providers, and context management moved from SDK to orchestrator
2. **Registry → Core**: Unified registry moved from SDK to core for shared access
3. **Service Pattern**: SDK now uses ServiceLocator to access orchestrator services
4. **Clear Boundaries**: Each layer now has distinct responsibilities
5. **🚀 Nested Architecture Upgrade**: Transformed all major subsystems with nested `NodeType`-based organization for massive performance gains

### 🚀 Performance Revolution

Our latest nested architecture upgrade delivers:
- **🎯 O(1) domain-specific queries** instead of O(n) scanning
- **📊 Built-in analytics and monitoring capabilities**
- **⚡ 10-100x performance improvements** for large datasets
- **🔍 Organized data access patterns** by node type across memory, metrics, and context systems

➡️ **[View Complete Performance Details](docs/NESTED_ARCHITECTURE_UPGRADE.md)**

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