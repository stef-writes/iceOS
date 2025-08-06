Below is the agreed-upon glossary and relationship map.  
Place it anywhere in `docs/` (e.g. `glossary.md`) and cross-link freely.

────────────────────────────────────────  
iceOS Terminology & Object Relationships  
────────────────────────────────────────

1 Design-Time Artefacts
────────────────────────

Term | Essence | Key Class | Where It Lives | Notes / Not This
---- | ------- | --------- | -------------- | ---------------
Sketch | Free-form sticky note or quick text label; may omit `type`, `id`, or params | *N/A* | iceCanvas draft state only | Never serialized; loses meaning outside Canvas
Partial Blueprint | Mixed collection containing both **real** `NodeSpec` objects and **sketch placeholders** (`PartialNodeSpec`) | `PartialBlueprint` | `ice_core.models.mcp` | Allows incremental construction; fails only *light* checks (unique IDs, valid JSON)
Blueprint (capital-B) | Fully specified design-time workflow; **no** placeholders | `Blueprint` | `ice_core.models.mcp` & stored by MCP | Immutable after validation; any change ⇒ new `blueprint_id`
Component Definition | Package-agnostic description of a single tool/agent/workflow plus optional code snippets | `ComponentDefinition` | MCP `/components/validate` payload | Bridges Studio → Registry
Factory Function | Pure Python callable returning a `ToolBase` / `IAgent` / `Workflow` | developer code + `@tool_factory`, `@agent_factory` | Registered via `register_*_factory` | Source of truth for instantiation

2 Compile-Time Artefacts
─────────────────────────

Term | Essence | Key Class / Func | Who Produces | Notes
---- | ------- | ---------------- | ------------ | -----
Validated Component | Factory executed once, sample instance passes validators | MCP + `validate_component()` | Becomes immutable registry entry (`module:create_func`)
NodeConfig | Runtime-ready Pydantic model (`ToolNodeConfig`, `AgentNodeConfig`, etc.) | `convert_node_specs()` | Derived from a Blueprint; each node type has its own schema

3 Run-Time Artefacts
────────────────────

Term | Essence | Class / Object | Who Creates | Notes
---- | ------- | -------------- | ----------- | -----
Runtime DAG | In-memory graph of NodeConfig objects plus execution metadata | `networkx.DiGraph` inside Orchestrator | Built at run start; destroyed afterwards or persisted for provenance
Executor | Async function registered via `@register_node("tool" | "agent" | …)` | `ice_orchestrator.execution.executors.*` | Invoked per node; fetches fresh instance via factory
Tool Instance | Fresh object implementing `ToolBase` | `registry.get_tool_instance()` | Life-cycle: create → execute → GC
Agent Instance | Fresh object implementing `IAgent` (+ internal memory) | `registry.get_agent_instance()` | One per run; memory context is isolated

4 Component Types
──────────────────

Type | Definition | Relationship
---- | ---------- | ------------
Tool | Stateless utility; strict inputs/outputs; subclass of `ToolBase` | Superset contains `LLMOperator`
LLMOperator | Tool specialised for single LLM completion; validated prompt & provider fields | Executes via `llm_executor`
Agent | Stateful reasoning loop that can call Tools; implements `IAgent` | Executes via `agent_executor`
Agent-as-Tool | Wrapper exposing an Agent behind the Tool protocol for composition | Class: `ice_orchestrator.tools.agent_tool.AgentTool`

5 UI Surfaces & Their Tiers
───────────────────────────

UI Surface | Primary Tier | Role
---------- | ------------ | ----
iceCanvas | Design-time | White-board; author Sketch → PartialBlueprint → Blueprint
iceStudio | Compile-time | Component workbench; validates factories (MCP calls); previews behaviour
iceGraph | Run-time | DAG visualization & metrics during / after execution

6 Life-Cycle Walkthrough (Happy Path)
─────────────────────────────────────

Stage | Action | Artefact Flow
----- | ------ | -------------
1. Canvas | User sketches flow (sticky notes) | ⟶ *Sketches* in Canvas state
2. Canvas → Canvas | User adds params / converts placeholders | *PartialBlueprint* evolves
3. Studio | User opens placeholder → authors Python factory via NL chat | emits *ComponentDefinition* (with `tool_factory_code`)
4. MCP Validate | Executes factory once, validates instance | stores factory import path in Registry; returns ✅
5. Canvas | Placeholder replaced with real node (`tool_name`) | *Blueprint* now fully specified
6. Validate Blueprint | Canvas/Studio click **Validate Blueprint** | MCP validates dependency graph & schemas → stores *Blueprint* immutably
7. Run | Orchestrator converts Blueprint → NodeConfig DAG | builds Runtime DAG, executes executors
8. Monitor | iceGraph streams node events & metrics | User sees timing/cost, can debug

7 “Negative‐Space” Clarifications
──────────────────────────────────

Term | **Is NOT** | Reason
---- | ---------- | ------
Blueprint | Runtime DAG | Blueprint has no execution metadata; DAG is built per-run
Tool | Singleton | Every invocation uses factory to create a fresh instance
Agent | Tool | Different execution contract (stateful loop); can be wrapped **as** a Tool when desired
iceGraph | Editing canvas | Read-only visualization of *executing* or finished DAG

8 Package → Tier Mapping Cheat-Sheet
────────────────────────────────────

Tier | Packages / Entry Points
---- | ----------------------
Design-time | `ice_builder`, front-end Canvas code
Compile-time | `ice_api.api.mcp`, `ice_core.validation`, `ice_core.unified_registry`
Run-time | `ice_orchestrator` executors, services, metrics  
*Registry note:* `ice_core.unified_registry` is **read-only** at run-time; all writes occur in Compile-time tier.

9 Runtime Objects & Visualisations
───────────────────────────────────

Object | What It Is | Lifecycle | Visible In
------ | ----------- | ---------- | ----------
Blueprint | Immutable JSON artefact (design-time) – list of **NodeSpec**s & dependency edges | Stored by MCP after validation; ID = `sha256(content)[:12]` (same content ⇒ same ID); editing clones under new ID (`bp_deadbeef12` → `bp_deadbeef12_v2`) | Edited on **iceCanvas**
Runtime DAG | `networkx.DiGraph` of fully-validated **NodeConfig**s plus run-metadata (start/end, retries, cost) | Built at run start, destroyed after run (unless persisted) | Displayed on **iceGraph**
iceGraph | Read-only UI that streams events & metrics for the Runtime DAG | Exists only during/after a run | iceGraph panel / monitoring view

Immutability & Versioning
~~~~~~~~~~~~~~~~~~~~~~~~~
• Blueprint IDs are **content-addressable**: same ID ⇒ identical code & params.  
• Editing a Blueprint clones it under a new ID (`bp_1234` → `bp_1234_v2`).  
• PartialBlueprint supports PATCH-style edits while drafting; calling `finalize()` freezes it into an immutable Blueprint.  
• Runtime DAG never mutates the Blueprint; all execution state lives in run records.

────────────────────────────────────────  
This glossary is now canonical; use these terms verbatim in code comments, docs, and UI labels.