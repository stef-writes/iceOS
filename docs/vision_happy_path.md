# Frosty + Canvas + Repo Hub: Vision, Roadmap, and North‑Star Journey

This document synthesizes the product vision, concrete roadmap, and the end‑to‑end happy path into a single source that aligns Studio (code‑first), Canvas (visual design), Frosty (NL co‑creator), the Orchestrator (run‑time), and the Repo Hub (SSOT).

---

## Executive Summary

Frosty and Canvas enable users to move from a natural‑language idea to a production‑grade, multi‑node workflow. The Repo Hub is the single source of truth (SSOT) for all components and blueprints; Studio doubles as the compiler‑tier for authoring and validating components that are then immediately available to Canvas and the Orchestrator. Deterministic CI/CD and dockerized type‑checks/tests ensure reproducible, pinned behavior.

---

## SSOT: Repo Hub

- All components (tools, agents, workflows) and blueprints live in the Repo Hub behind the iceOS API.
- UIs (Studio, Canvas, Frosty) only talk to the API; Orchestrator rehydrates the registry at startup and post‑registration.
- Identifiers
  - Components: name + semver; content hash recorded for provenance.
  - Blueprints: content‑addressable IDs (derived from normalized JSON).
- Promotion gates: draft → released components; Canvas shows released by default.

---

## Three‑Tier Execution Model

Tier | Purpose | iceOS Packages & Key Objects
---- | ------- | ---------------------------
Design‑time (“Sketch / Canvas”) | Human‑readable plan; nodes may be incomplete or placeholders | `ice_builder` (Draft DSL, WorkflowBuilder) → emits Pydantic `Blueprint` models
Compile‑time (“Studio / Build”) | Full structural & behavioral validation; generates immutable import paths | `ice_api.api.mcp` validation routes; `ComponentDefinition` (`tool_factory_code`, …); `ice_core.validation.*`; registers via `ice_core.unified_registry`
Run‑time (“Execute / Orchestrator”) | Deterministic execution of validated nodes | `ice_orchestrator` DAG engine + node executors; factories invoked via registry

Guarantees
- Schema correctness (Design) → enforced by Pydantic models.
- Behavioral correctness (Compile) → factory executed once, instance validated, signature vs args matched.
- Safe execution (Run) → fresh instance per run, quick `isinstance` asserts, sandbox/timeout limits.

---

## Roles: Canvas, Studio, MCP, Orchestrator

Component | Role | Mapping to 3‑tier model
--------- | ---- | ----------------------
iceCanvas (whiteboard UI) | Brainstorming & layout. Drag placeholders or drop pre‑built components. Outputs draft `Blueprint`. | Operates in Design‑time tier.
iceStudio (component workbench) | Turn a placeholder into a real Tool/Agent/Workflow. Templates, NL code gen, live previews. | Interface to Compile‑time. On Validate, calls MCP `/components/validate`.
MCP (Model‑Compile Pipeline) | Headless compile service; executes factory once, validates, records import paths in registry. | Implements Compile‑time tier API.
Orchestrator | Executes a blueprint; pulls fresh instances via factory paths from registry. | Implements Run‑time tier.

---

## North‑Star Happy Path — Idea → Draft → Blueprint → Running Workflow

### 1 · User Idea

> “I have a CSV of clearance items. Create draft marketplace listings, price them with a 25% margin, and show me a dashboard of successes vs failures.”

The user shares this with Frosty (CLI, VS Code, or Slack).

### 2 · Frosty ⇒ Draft (Design‑time, zero‑schema)

1) Intent detection → pipeline.
2) Plan synthesis → `load_csv → loop rows → pricing → copy generator → upload → aggregate`.
3) Produce a Draft (partial blueprint) with placeholders (no validation yet):

```jsonc
{
  "blueprint_id": "draft_a12b",
  "schema_version": "1.1.0",
  "nodes": [
    {"id": "load_csv", "type": "tool", "tool_name": "csv_loader"},
    {"id": "loop_products", "type": "loop", "items_source": "load_csv.rows"}
  ],
  "metadata": {"draft_name": "Clearance Listings v0"},
  "is_complete": false
}
```

### 3 · Canvas Renders the Draft (UI design‑time)

Grey placeholders appear:

```
[CSV Loader] → [Loop Products] → [???] → [Aggregator]
```

- Hovering suggests completions (Pricing Strategy, Listing Agent, …).
- Drag blocks; Canvas wires edges automatically.
- Canvas persists incremental edits via MCP endpoints.

### 4 · Fill Gaps in Studio (Compiler‑tier, optional but common)

If a referenced component (e.g., `pricing_strategy`) doesn’t exist:
- Open Studio from Repo Hub with a “new tool” stub.
- Author code (class/factory), specify schemas, preview in WASM sandbox.
- Validate & Register via MCP (`/components/validate` then register on success).
- Registration writes to Repo Hub → Orchestrator rehydrates → Canvas palette updates instantly.

### 5 · Draft ⇒ Partial ⇒ Blueprint (strict schema)

- Save partial: `PUT /blueprints/partial/{id}`.
- Finalize: `POST /blueprints/partial/{id}/finalize` returns a validated Blueprint:

```jsonc
{
  "blueprint_id": "bp_99e8",
  "nodes": [
    {"id": "load_csv", "type": "tool", "tool_name": "csv_loader"},
    {"id": "loop_products", "type": "loop", "items_source": "load_csv.rows"}
  ],
  "metadata": {"owner": "alice"}
}
```

All design‑time errors (missing deps, cycles, schema mismatch) are blocked here.

### 6 · Compile‑time Resolution (Registry + Manifest)

`Workflow.from_blueprint()`:
1) Resolve node references via Repo Hub registry.
2) Build strict, version‑pinned `NodeConfig` objects.
3) Emit a frozen JSON manifest (GitOps/audit/CI artifact).

### 7 · Run‑time Execution (lenient bus)

```
Workflow → NodeExecutor (retry/cache/budget) → Unified Executors → Tool / LLM / Code
```

- NodeExecutor validates `input_schema`, enforces retry/budget/timeout, passes a rich context dict.
- Executors accept extra kwargs (`additionalProperties: true`) for forward‑compatibility.
- Outputs validated before re‑entering the bus.

This “strict‑edge / lenient‑bus” mirrors Airflow XCom, Prefect Results, Dagster OpContext.

### 8 · Live Feedback

- WS events: `workflow.started`, `node.started`, `node.finished`, `workflow.finished`.
- Canvas paints progress in real time; Frosty summarizes: “9 listings succeeded, 0 failed.”

### 9 · Iteration

User: “Change margin to 30% and re‑run only failed items.”
Frosty patches the Blueprint (or Canvas edit). Orchestrator executes incrementally; Canvas updates live.

### 10 · Deployment

`POST /mcp/runs` launches the frozen blueprint in staging (`max_parallel=10`).
GitOps records manifest + component versions; promotion gates manage exposure in Canvas.

---

## Environments & Determinism

- Type‑check (mypy) and unit tests run inside Docker stages (devcheck/test) with pinned Python (3.11.9) and dependencies exported from the lock → no drift.
- Test stage bakes env flags for stable semantics:
  - `ICE_ENABLE_INLINE_CODE=1`
  - `ICE_COMPUTE_GRAPH_CENTRALITY=1`
  - `ICE_STRICT_SERIALIZATION=1`
- CI never mutates the lock: `poetry lock --check`; unit tests run in Docker.

---

## APIs Cheat‑Sheet

- Components (Repo Hub):
  `GET /components` · `GET /components/{type}/{name}`
  `POST /components/validate` (Studio) → registers on success
- Drafts / Blueprints (Canvas):
  `POST /blueprints/partial` · `PUT /blueprints/partial/{id}` · `POST /blueprints/partial/{id}/finalize`
  `GET /blueprints/{id}`
- Runs (Orchestrator):
  `POST /mcp/runs` · `GET /mcp/runs/{run_id}` · `GET /mcp/runs/{run_id}/events` (SSE/WS)

---

## Traceability Cheat‑Sheet

Step | Code call‑path
---- | --------------
Register factory | `@tool_factory` → `register_tool_factory`
Validate factory | MCP `validate_component()`
Runtime create | `tool_executor` → `registry.get_tool_instance`
Error surfaces | Compile error in Studio; or `TypeError` in executor if factory signature mismatches

---

## Strategic Goals

### Near‑term (0‑6 months)
1. Production‑Ready Frosty: NL → blueprint conversion with 90%+ success
2. Canvas MVP: spatial workflow editor with real‑time collaboration
3. Multi‑Level Translation: Support Tool → Node → Chain → Workflow

### Mid‑term (6‑12 months)
1. Visual Programming: drag‑drop with AI‑assisted connections
2. Intelligent Suggestions: context‑aware, canvas‑state driven
3. Team Collaboration: multi‑user editing with conflict resolution

### Long‑term (12‑24 months)
1. Sketch‑to‑Workflow conversion
2. Ambient intelligence (learn from usage)
3. Enterprise scale (10K+ node workflows, sub‑second interactions)

---

## Success Stories (Already Achieved)

### Incremental Blueprint Construction

```python
# Production API endpoints
POST   /api/mcp/blueprints/partial              # Create new partial
PUT    /api/mcp/blueprints/partial/{id}         # Add/remove/update nodes
POST   /api/mcp/blueprints/partial/{id}/finalize # Convert to executable

# Live validation with AI suggestions
partial._validate_incremental()
# Returns: {"next_suggestions": [{"type": "llm", "reason": "Process tool output"}]}
```

Impact: Canvas can build incrementally with live validation and AI assistance.

### Unified Memory System

```python
memory = UnifiedMemory(UnifiedMemoryConfig(
    enable_working=True,
    enable_episodic=True,
    enable_semantic=True,
    enable_procedural=True,
))
```

Impact: Agents remember context, learn from interactions, and improve.

### 20+ Production Tools

- File ops, data processing, web scraping
- API integrations, DB queries, ML inference
- All with automatic validation and cost tracking

---

## Phase Roadmap

### Phase 1: Frosty Intelligence Layer (Q1 2025)

1.1 Multi‑Level Translation Engine (Tool/Node/Chain/Workflow)
- Weeks 1‑2: Tool‑level translation
- Weeks 3‑4: Node‑level translation
- Weeks 5‑6: Chain‑level translation
- Weeks 7‑8: Workflow‑level translation

Success Metrics: Tool >95%, Node >90%, Chain >85%, Workflow >80% accuracy.

1.2 Context‑Aware Intelligence
- Workspace analysis, intent classification, confidence scoring, learning loop

### Phase 2: Canvas Spatial Platform (Q2 2025)

2.1 Text‑First Canvas: spatial regions, text blocks, auto‑layout, region context
2.2 Visual Component Library: node palette, connections, execution indicators, property panels

### Phase 3: Collaborative Intelligence (Q3 2025)

- Real‑time collaboration via WS events; CRDT/AI‑mediated conflict resolution
- Presence, region locking, change history, role‑aware suggestions

### Phase 4: Visual Intelligence (Q4 2025)

- Structured sketch recognition → constrained shapes and template matching
- Progressive rollout to freeform sketches with confidence‑gated conversion

---

## Success Metrics & KPIs

### Technical Performance

| Metric | Current | Target Q1 | Target Q2 | Target Q4 |
|--------|---------|-----------|-----------|-----------|
| API Response Time | <50ms | <40ms | <30ms | <25ms |
| Canvas Load (1K nodes) | N/A | <3s | <2s | <1s |
| Translation Accuracy | 60% | 85% | 90% | 95% |
| Collaboration Latency | N/A | <200ms | <100ms | <50ms |

### User Experience

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to First Node | <30s | Landing → working node |
| Daily Active Users | 1000+ | Unique users per day |
| Workflow Completion Rate | >80% | Started vs published |
| User Correction Rate | <10% | Corrections per interaction |

### Business Impact

| Metric | Baseline | Year 1 Target |
|--------|----------|---------------|
| Workflows Created | 0 | 10,000+ |
| Avg Nodes/Workflow | N/A | 15+ |
| Team Adoption | 0 | 100+ teams |
| Enterprise Customers | 0 | 10+ |

---

## Technical Architecture Evolution

Current State (Production)
```
Frosty CLI → ice_builder → MCP API → Orchestrator
    ↓           ↓            ↓           ↓
Simple NL   Blueprint   Validation   Execution
```

Target State (End of Roadmap)
```
Canvas UI ←→ Frosty AI ←→ Collaboration Engine
    ↓            ↓              ↓
Spatial      Intelligent    Real‑time
Interface    Assistance     Multi‑user
    ↓            ↓              ↓
         MCP API (Enhanced)
              ↓
    Distributed Orchestrator
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Canvas Performance | High | WebGL rendering, viewport virtualization |
| Sketch Accuracy | Medium | Start structured; confidence thresholds; user confirmation |
| Real‑time Conflicts | Medium | CRDT algorithms; optimistic updates; AI mediation |
| LLM Latency | Low | Edge caching, streaming |

---

## Why Strict‑Edge / Lenient‑Bus

| Layer | Validation | Reason |
|-------|------------|--------|
| REST / SDK / Blueprint | Strict (`additionalProperties=false`) | Governance, reproducibility, API contracts |
| Internal DAG Context | Lenient (kwargs, extras) | Composability, AI‑generated nodes, future proof |

This dual contract lets Frosty & Canvas add or rearrange nodes safely while guaranteeing deterministic deployment artifacts.

---

## Next Steps

1) Finalize Q1 development priorities.
2) Begin Canvas UI prototyping; wire MCP partial edits.
3) Expand Frosty training data; close the loop with correction learning.
4) Enforce deterministic CI: dockerized mypy/tests; `poetry lock --check`.

---

Last Updated: January 2025 · Status: Active Development · Version: 1.0
