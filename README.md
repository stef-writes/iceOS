# iceOS – The AI-Native Operating Layer for Agentic Workflows

> **Docs moved!**  This README is now a high-level overview.  Full, versioned documentation lives in the `docs/` folder and will be published at https://stef-writes.github.io/iceOSv1-A-.  Start with `docs/index.md` or run `mkdocs serve`.

> **Build, run & scale reliable multi-agent AI systems in minutes.**

[![CI](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml/badge.svg)](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml)

---

## 🎯 **What We're Building**

**iceOS** is the **"Docker for AI workflows"** - a developer-first orchestration engine that lets you build complex AI systems as declarative DAGs with production-ready tooling.

Think of it as **"Kubernetes for AI agents"** - you define your workflow in code, and iceOS handles the execution, scaling, monitoring, and reliability.

---

## 🚀 **Why iceOS? (The Problem We Solve)**

Every AI product team faces the same challenges:
- **Glue Code**: Stitching together OpenAI + LangChain + custom tools
- **Boilerplate**: Re-implementing retry logic, caching, cost controls
- **Debugging**: No visibility into complex multi-step AI workflows
- **Production**: Missing guardrails, monitoring, and error handling

**iceOS solves this** by providing a **production-ready orchestration engine** with built-in:
- ✅ Retry logic & circuit breakers
- ✅ Cost tracking & token management  
- ✅ OpenTelemetry tracing
- ✅ Type-safe node configurations
- ✅ Plugin ecosystem for tools

---

## 🏗️ **Current State: Developer-First Foundation**

### **What's Built Today**
```python
# Define your workflow as a DAG
from ice_orchestrator import ScriptChain
from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig

nodes = [
    AiNodeConfig(id="analyzer", prompt="Analyze: {{input}}"),
    ToolNodeConfig(id="email", tool_name="EmailTool", dependencies=["analyzer"])
]

# Execute with production tooling
chain = ScriptChain(nodes=nodes)
result = await chain.execute()
```

### **Core Capabilities**
- **Node Types**: AI, Tool, Condition, Agent, Webhook
- **Execution Engine**: Level-based parallel execution
- **Developer Tools**: CLI, type checking, auto-discovery
- **Production Features**: Caching, retries, cost tracking, tracing

---

## 🎯 **Vision: "Figma for AI Workflows"**

**Phase 1: Developer Foundation** ✅ *(Current)*
- Robust orchestration engine
- Growing tool ecosystem  
- CLI-first developer experience

**Phase 2: Visual Layer** 🚧 *(Next)*
- Infinite canvas whiteboard
- Drag & drop node composition
- Text-to-workflow generation
- Real-time collaboration

**Phase 3: AI-Powered** 🔮 *(Future)*
- "Frosty Copilot" - AI assistant for workflow design
- Auto-optimization based on telemetry
- Self-improving workflows

---

## 🛠️ **Quick Start (2 min)**

```bash
# 1. Install iceOS
pip install iceos

# 2. Create your first workflow
ice create tool HelloTool             # scaffolds HelloTool.tool.py
ice create chain hello_chain          # scaffolds hello_chain.chain.py
ice run hello_chain.chain.py          # executes the chain

# 3. Or run the demo (optional)
python scripts/demo_run_chain.py
```

### **Docker Option**
```bash
docker build -t iceos .
docker run --rm -p 8000:8000 iceos
# Visit http://localhost:8000/docs
```

---

## 🏛️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    Developer Interface                      │
│  CLI Commands  │  API Endpoints  │  Visual Canvas (v2)   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 iceOS Runtime Engine                       │
│  • ScriptChain execution                                  │
│  • OpenTelemetry tracing                                  │
│  • Cost management                                        │
│  • Circuit breakers                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Node Ecosystem                          │
│  AI Nodes  │  Tool Nodes  │  Condition Nodes  │  Agents  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 **Roadmap: Close to Major Milestone**

### **Q3 2025: ScriptChain Runtime GA** 🚧 *(Current Focus)*
- **Target**: Production-ready orchestration engine
- **Status**: 75% complete - need final coverage push
- **Milestone**: 95%+ test coverage, circuit breakers, performance optimization

### **Q4 2025: Developer CLI GA** 📋
- **Target**: Complete CLI experience for workflow development
- **Features**: Interactive builders, hot-reload, auto-registration
- **Milestone**: `ice chain wizard` → `ice chain run --watch`

### **Q1 2026: Visual Layer Alpha** 🎨
- **Target**: First visual workflow designer
- **Features**: Drag & drop, infinite canvas, real-time preview
- **Milestone**: "Figma for AI workflows" MVP

### **Q2 2026: Frosty Copilot Beta** 🤖
- **Target**: AI-powered workflow generation
- **Features**: Text-to-workflow, auto-optimization, collaboration
- **Milestone**: Natural language workflow creation

---

## 🏆 **Competitive Advantages**

| Feature | LangChain | n8n | **iceOS** |
|---------|-----------|-----|-----------|
| **Architecture** | Library | Visual | **Engine + CLI** |
| **Production** | DIY | Basic | **Built-in** |
| **Developer UX** | Code-only | No-code | **CLI-first** |
| **Extensibility** | Python | 400+ nodes | **Plugin ecosystem** |
| **Guardrails** | None | Basic | **Enterprise-grade** |

---

## 🛠️ **Current Capabilities**

### **Orchestration Engine** ✅
- Async ScriptChain execution
- Level-based parallel processing
- Dependency resolution
- Failure policies & retry logic

### **Node Ecosystem** ✅
- AI nodes (OpenAI, Anthropic, Gemini, DeepSeek)
- Tool nodes (HTTP, File, Email, Custom)
- Condition nodes (branching logic)
- Agent nodes (multi-turn conversations)

### **Developer Tools** ✅
- CLI with auto-discovery
- Type-safe configurations
- Hot-reload development
- Comprehensive testing

### **Production Features** ✅
- OpenTelemetry tracing
- Cost tracking & token management
- Caching & performance optimization
- Error handling & circuit breakers

---

## 🚀 **Getting Started**

### **For Developers**
```bash
# Install
pip install iceos

# Create your first tool
ice create tool MyTool

# Create your first chain
ice create chain my_workflow

# Execute the workflow
ice run my_workflow.chain.py
```

### **For Teams**
```bash
# Set up CI/CD
make test
make lint
make doctor

# Deploy to production
docker build -t iceos .
docker run -p 8000:8000 iceos
```

---

## 🤝 **Community & Support**

- **GitHub Discussions**: Share workflows, get help
- **Slack**: `ice-community.slack.com` for real-time chat
- **Commercial Support**: `team@iceos.ai` for enterprise needs

---

## 📄 **License**

iceOS is **MIT-licensed** - free for personal & commercial use. We welcome contributions!

---

## 🧪 **Development**

```bash
# Full test suite
make test

# Lint & type check
make lint

# Health check (everything)
make doctor

# Clean up
make clean
```

---

> **We're close to our first major product milestone!** The ScriptChain runtime is nearly production-ready, and we're building the foundation for the visual layer that will democratize AI workflow creation.

> *Last updated: July 2025*
