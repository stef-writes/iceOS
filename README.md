# iceOS – The AI-Native Operating Layer for Agentic Workflows

> **Build, run & scale reliable multi-agent AI systems in minutes.**

[![CI](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml/badge.svg)](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/iceos.svg)](https://pypi.org/project/iceos/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 **What We're Building**

**iceOS** is an AI-native orchestration engine.  It lets you define complex multi-agent workflows as declarative DAGs and then executes them with built-in scaling, monitoring, and reliability controls.

---

## 🧠 **Why iceOS Exists**

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

## ✨ **Key Features**

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
| Feature | Benefit |
|---------|---------|
| Node types: AI, Tool, Condition, Agent, Webhook | Flexible workflow design |
| Level-based execution engine | Optimised parallel processing |
| CLI, type checking, auto-discovery | Developer ergonomics |
| Caching, retries, cost tracking, tracing | Production guardrails |

---

## 🧬 **Core Concepts: AiNode & ScriptChain**

iceOS revolves around two primitives that power every workflow:

1. **AiNode – the reasoning block**
   - LLM prompt + validation + retry/back-off in a single, type-safe unit.
   - May be granted **multiple tools** (agent-style, adaptive) or **one/no tool** (deterministic specialist).
   - Emits structured, Pydantic-validated output that downstream nodes can trust.

2. **ScriptChain – the orchestrator kernel**
   - Converts a static DAG of nodes into a *level-parallel*, token-/depth-guarded execution plan.
   - Enforces failure policies (`HALT`, `CONTINUE_POSSIBLE`, `ALWAYS`), caching, branch gating, and cost ceilings.
   - Streams OpenTelemetry spans + cost metrics so ops teams get observability out-of-the-box.

Read the full deep-dive in [`docs/core_concepts.md`](docs/core_concepts.md) – it covers tool modes, execution flow diagrams, and a runnable 20-line example.

---

## 🎯 **Vision & Phases**

**Phase 1 – Developer Foundation** ✅ *(Current)*  
Robust orchestration engine: ScriptChain, cost guard-rails, tracing.

**Phase 2 – Visual Layer** 🚧 *(Next)*  
Infinite canvas whiteboard, drag-and-drop nodes, real-time preview.

**Phase 3 – AI-Assisted Design (Frosty v1)** 🔮  
Text-to-workflow generation, self-reflection loop, cost hot-spot surfacing.

**Phase 4 – MCP & Blueprint Runtime** 🛰️  
Versioned Model Context Protocol server, streaming node telemetry.

**Phase 5 – Live Collaboration** 🎥  
Embedded video/voice, shared cursors, real-time transcripts feeding Frosty.

**Phase 6 – Ecosystem & Marketplace** 🌐  
Third-party node marketplace, template exchange, revenue-sharing.

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

### 🧑‍💻 Developer Experience – CLI scaffolding
```bash
ice create tool CustomTool
ice create chain data_pipeline
ice run data_pipeline.chain.py
```

### 🛠️ Installation Options
| Scenario | Command |
|----------|---------|
| Minimal production (no demo code) | `poetry install --only main` |
| Full demo environment | `poetry install --with demos` |

### **Docker Option**
```bash
docker build -t iceos .
docker run --rm -p 8000:8000 iceos
# Visit http://localhost:8000/docs
```

---

## 🧩 **New in v0.5 – Nested Chains & Networks**

iceOS workflows can now call entire *ScriptChains* as if they were single nodes and you can wire multiple chains together in a one-page YAML file:

```bash
# 1. Register a reusable chain once (e.g. payment_processing.py)
python payment_processing.py  # module registers the chain at import-time

# 2. Create your network spec
ice create network checkout_net
# edit checkout_net.network.yaml …

# 3. Execute
ice run-network checkout_net.network.yaml
```

`nested_chain` nodes wrap a child `ScriptChain` while `network.v1` YAML lets you describe an entire "system of chains" declaratively:

```yaml
api_version: "network.v1"
metadata:
  name: checkout_net
nodes:
  total:
    type: ai
    model: gpt-4o
    prompt: "Cart total: {items}"

  payment:
    type: nested_chain
    chain_id: "payment_processing@1.2.0"
    dependencies: ["total"]
```

CLI additions:

| Command | Purpose |
|---------|---------|
| `ice create network <name>` | Scaffold a `*.network.yaml` template |
| `ice run-network <spec.yaml>` | Build & execute the network |

These new surfaces push us closer to **text-to-workflow** → **text-to-network**: describe intent in natural language, let the Copilot (coming soon) generate the spec, and iceOS runs it with full observability & guardrails.

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

## 🌈 **Vision Roadmap**

| Quarter | Phase | Milestone | Key Deliverables |
|---------|-------|-----------|------------------|
| **Q3 2025** | 1 | ScriptChain Runtime GA | 95% test coverage, retries, cost tracking, OpenTelemetry |
| **Q4 2025** | 2 | CLI GA & Visual Layer Alpha | `ice chain wizard`, Canvas MVP, drag-and-drop nodes |
| **Q1 2026** | 3 & 4 | Frosty v1 + MCP Foundation | `generate_blueprint`, `run_blueprint`, SSE telemetry, versioned MCP spec |
| **Q2 2026** | 4 | Self-Reflection Loop | Frosty analyses live traces, auto-optimise blueprints |
| **Q3 2026** | 5 | Live Collaboration MVP | LiveKit integration, shared cursors, transcript feed into Frosty |
| **Q4 2026** | 6 | Marketplace Beta | Node/template marketplace, billing + quota API |
| **Q1 2027** | 7 | Proprietary Planner Model | Anonymised transcript & graph dataset, fine-tuned model deploy |
| **Q2 2027** | 8 | Spatial Canvas Preview | 3D workflow visualisation, VR meeting support |

*All phases are feature-flagged and gated by KPIs defined in the strategy documents.*

---

## 🏆 **Core Strengths**

- **Production-ready execution**: retries, caching, cost tracking, tracing.
- **Modular node ecosystem**: AI, tool, condition, agent, webhook nodes.
- **Developer ergonomics**: CLI scaffolding, hot-reload, type-safe configs.
- **Governance & compliance**: BudgetEnforcer, safety validators, audit logs.

### Competitive Landscape

| Capability | LangChain | Airflow | **iceOS** |
|------------|-----------|---------|-----------|
| Orchestration focus | Library functions | Batch scheduler | AI-native DAG engine |
| Visual design | Limited (LangGraph) | DAG graph only | Infinite canvas & real-time collab |
| AI node type | External hack | None | First-class (AiNode) |
| Guardrails & cost | Manual | Ops-centric SLA | Budget + safety validators |
| Extensibility | Python modules | Plugins | Python + `.tool.py` auto-registration |
| Execution telemetry | Minimal | Task logs | OpenTelemetry spans + cost metrics |

*iceOS differentiates by combining AI-first nodes with enterprise-grade execution guardrails and a visual design layer out-of-the-box.*

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
# Contributor quick-start (one-time setup)
poetry install --with dev
make doctor

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
