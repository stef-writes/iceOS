# iceOS - AI Workflow Orchestration System

**Transform natural language into executable AI workflows with enterprise-grade security and cognitive memory.**

## 🔌 **Model Context Protocol (MCP) Server**

**iceOS is now the most sophisticated MCP server available**, exposing entire enterprise workflow orchestration capabilities through standard MCP interfaces.

```bash
# Start iceOS as MCP server
uvicorn ice_api.main:app --host 0.0.0.0 --port 8000

# Available at: http://localhost:8000/mcp/
# MCP capabilities: tools, resources, prompts, notifications
```

**What makes iceOS MCP unique:**
- ✅ **Enterprise Workflows**: Execute complete multi-step AI workflows, not just simple tools
- ✅ **Memory-Enabled Agents**: Agents with persistent episodic, semantic, and procedural memory
- ✅ **Real Integrations**: arXiv search, Yahoo Finance, Reddit sentiment, CSV processing, and more
- ✅ **Multiple Transports**: HTTP JSON-RPC + stdio support for any MCP client

👉 **[Complete MCP Documentation](docs/MCP_IMPLEMENTATION.md)**

## 🎯 **What You Can Build**

```python
# Real-world example: Document processing with intelligent memory
workflow = (WorkflowBuilder("Document Assistant")
    .add_tool("parse", "document_parser", file_path="docs/")
    .add_tool("chunk", "intelligent_chunker", strategy="semantic")
    .add_agent("chat", "document_chat_agent", 
               memory={"enable_episodic": True, "enable_semantic": True})
    .connect("parse", "chunk")
    .connect("chunk", "chat")
    .build()
)

# Execute with real data
result = await WorkflowExecutor().execute(workflow, {
    "user_query": "What are the key insights from these financial reports?"
})
```

## 🧠 **Cognitive Memory System**

Unlike other AI frameworks that just vectorize conversations, iceOS implements **human-like memory**:

- **🔧 Working Memory**: Active conversation state (expires in minutes)
- **📚 Episodic Memory**: "Remember when customer X negotiated and bought for $420"
- **🎯 Semantic Memory**: "iPhone 13 market price is $580, demand is high" 
- **⚙️ Procedural Memory**: "Use strategy Y for electronics - 85% success rate"

```python
# Agents learn and improve over time
customer_history = await agent.memory.episodic.search(f"customer:{customer_id}")
best_strategy = await agent.memory.procedural.get_best_strategy("pricing")
market_data = await agent.memory.semantic.get_facts_for_entity("iPhone_13")
```

## 🚀 **Real-World Demos**

### **📚 Document Assistant** - Enterprise Document Processing
- **Real PDF/Word parsing** with intelligent chunking
- **Semantic search** across document collections  
- **Memory-powered chat** that remembers document context
- **Run**: `python use-cases/DocumentAssistant/run_blueprint.py`

### **🛒 Facebook Marketplace Seller** - E-commerce Automation  
- **Real CSV inventory** processing and AI enhancement
- **Customer service agent** with conversation memory
- **Dynamic pricing agent** using market intelligence
- **Run**: `python use-cases/RivaRidge/FB_Marketplace_Seller/run_blueprint.py`

### **🧠 BCI Investment Intelligence** - Financial Research AI
- **Real arXiv paper** analysis for investment research
- **Multi-agent collaboration** with recursive communication
- **All 9 node types** demonstrated in one sophisticated workflow
- **Run**: `python use-cases/BCIInvestmentLab/run_blueprint.py`

## ✨ **Why iceOS?**

### **🎨 Simplified Developer Experience**
```python
# Fluent API - describe what you want, not how to wire it
workflow = (WorkflowBuilder("Sales Analysis")
    .add_tool("read_csv", "csv_reader", file="sales.csv")
    .add_llm("analyze", "gpt-4", "Analyze this sales data: {{read_csv.output}}")
    .add_agent("insights", "insights_agent", tools=["trend_analyzer"])
    .connect("read_csv", "analyze")
    .connect("analyze", "insights")
    .build()
)
```

### **🛡️ Enterprise Security**
- **WASM sandboxes** for user code execution
- **Resource limits** with CPU/memory monitoring
- **Network isolation** and import restrictions
- **Audit logging** with OpenTelemetry integration

### **🧠 Intelligent Agents**
- **Learn from experience** with 4-tier memory system
- **Improve strategies** based on success metrics
- **Context awareness** across conversations
- **Domain expertise** through organized knowledge

## 🏗️ **Architecture**

iceOS follows a clean 4-layer architecture with strict boundaries:

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

### **Layer Responsibilities**
- **ice_core**: Shared models, protocols, unified registry
- **ice_sdk**: Developer tools, workflow builders, fluent APIs  
- **ice_orchestrator**: Runtime execution, cognitive memory, security
- **ice_api**: HTTP/WebSocket interfaces, blueprint validation

## 🚀 **Quick Start**

### **Installation**
```bash
# Clone and install
git clone https://github.com/your-org/iceos.git
cd iceos
poetry install

# Run a real demo
python use-cases/DocumentAssistant/run_blueprint.py
```

### **Your First Workflow**
```python
from ice_sdk.builders import WorkflowBuilder
from ice_orchestrator.execution.executor import WorkflowExecutor

# Create workflow
workflow = (WorkflowBuilder("Hello iceOS")
    .add_tool("fetch", "http_request", url="https://api.github.com/users/octocat")
    .add_llm("summarize", "gpt-4", "Summarize this profile: {{fetch.output}}")
    .connect("fetch", "summarize")
    .build()
)

# Execute
result = await WorkflowExecutor().execute(workflow, {})
print(result.outputs["summarize"].content)
```

### **Create Your First Tool**
```python
from ice_sdk.tools.base import ToolBase
from ice_sdk.decorators import tool

@tool  # Auto-registers as "weather_checker"
class WeatherChecker(ToolBase):
    """Check weather for a city."""
    
    async def _execute_impl(self, city: str) -> dict:
        # Your weather API logic here
        return {"weather": f"Sunny in {city}", "temp": 72}
```

## 📊 **Performance & Security**

### **🚀 O(1) Memory Access**
```python
# Get domain-specific data instantly
marketplace_entities = memory.semantic.get_entities_by_domain('marketplace')
pricing_strategies = memory.procedural.get_procedures_by_category('pricing')
```

### **🛡️ WASM Sandboxing**
- User code runs in **WebAssembly containers**
- **CPU/memory limits** enforced
- **Network isolation** and import restrictions
- **Audit trails** for compliance

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