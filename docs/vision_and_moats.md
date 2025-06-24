# iceOS – Vision, Current Capabilities & Roadmap

> Last updated: 2025-06-14

---

## 0. Executive Summary

iceOS is an **AI-native orchestration platform**.  Today the repo already ships:

* a type-safe SDK (`ice_sdk`)
* an async workflow engine (`ice_orchestrator`)
* a FastAPI service layer (`app`)

The broader vision adds autonomous planning, guard-railed execution and a
copilot UI.  This document separates **what is available now** from
**what we are building next** so everyone shares the same map.

---

## 1. Current Capabilities (v0.x)

| Layer | Implemented Highlights |
|-------|------------------------|
| **FastAPI Application** (`src/app`) | • Root health-check `/`  • V1 API endpoints for executing a single node or a full chain |
| **Orchestration Engine** (`ice_orchestrator`) | • Async `ScriptChain` executes `AiNode` & `ToolNode` DAGs  • Basic dependency graph |
| **Core SDK** (`ice_sdk`) | • Pydantic node / tool configs  • `AgentNode` wrapper for LLM calls  • `LLMService` with OpenAI, Anthropic, Gemini & DeepSeek handlers  • `GraphContextManager`  • **New** `ice_sdk.interfaces` module that exposes lightweight `Protocol`s (e.g. `ScriptChainLike`) so inner layers never import outer ones |
| **Tools** (`ice_sdk.tools`) | • `BaseTool` abstraction  • Hosted: `WebSearchTool`, `FileSearchTool`, `ComputerTool`  • Deterministic: `SleepTool`, `HttpRequestTool`, `SumTool` |
| **Quality Tooling** | • Ruff & isort  • Black  • MyPy (strict)  • Pyright (basic mode)  • Import-linter contracts  • Pre-commit with auto-format  • Unit & integration tests (coverage ≥56 %) |

**Not implemented yet**  
Planner / Verifier / Ensemble agents • Depth/Token/Semantic guardrails •
Context Blocks & Composite Nodes • Frosty UI • Tool Marketplace • Telemetry
loop • WASM runner

---

## 2. Strategic Vision (12-Month Outlook)

1. **Frosty Copilot** – natural-language canvas that generates, explains and
   refactors workflows.
2. **Guard-railed Runtime** – depth, token & semantic limits with policy
   plug-ins.
3. **Extensible Ecosystem** – verified tool marketplace, shareable workflow
   library, versioned `IceWorkflowSpec`.
4. **Self-Improving Engine** – telemetry-driven optimisers that rewrite DAGs.

These pillars underpin our strategic moats: orchestration complexity,
layered guardrails, ecosystem lock-in and data network effects.

---

## 3. Roadmap (Q3 2025 — agility-first)

The long-term vision (copilot UI, marketplace, self-improving engine) remains. The short-term priority is to make iceOS **immediately useful and reusable**.

| Week | Focus | Outcome |
|------|-------|---------|
| **1** | v0.2 minimal release | Safe-mode guard, PyPI wheel, example chain |
| **2** | Developer CLI | `ice new`, `ice run --watch`, auto-registration |
| **3** | API freeze & packaging | Stable SDK exports, generated docs, optional extras, manylinux wheel |
| **4** | Examples & community | Reusable workflow recipes, Discussions board, Slack channel |

Details live in [`docs/roadmap_agile.md`](roadmap_agile.md).

---

## 4. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **LLM Provider Shifts** | Keep `LLMService` adapter pattern; add local-model handler |
| **OSS Competition** | Differentiate via deep guardrails & enterprise governance |
| **Type-Safety Erosion** | "No new Pyright errors" pre-commit hook |
| **Security Debt** | `pip-audit` enforced in CI + OWASP review |

---

## 5. Additional Reference Docs

* [`competitive_landscape.md`](competitive_landscape.md) – live comparison with Workflow86 / LangGraph / n8n and the text-to-flow action plan.

---

> This document is the single source of truth for **current capabilities** and
> the forward **roadmap**.  Update the Current Capabilities table and roadmap
> checkpoints at the end of every sprint. 