# North-Star User Journey  – From Idea → Draft → Blueprint → Running Workflow

*A concise happy-path that illustrates how Frosty + Canvas + iceOS work together to turn a single natural-language idea into a production-grade, multi-node workflow.*

---

## 1 · User Idea

> “I have a CSV of clearance items. Create draft marketplace listings, price them with a 25 % margin, and show me a dashboard of successes vs failures.”

The user types this sentence into **Frosty** (CLI, VS Code sidebar, or Slack bot).

---

## 2 · Frosty ⇒ *Draft*  (Design-time, zero-schema)

1. **Intent detection** – recognises a *pipeline*.
2. **Plan synthesis** – decides high-level steps: `load_csv → loop rows → pricing → copy generator → upload → aggregate`.
3. **Partial Blueprint / Draft** – serialised JSON with node stubs and metadata; no validation yet.

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

---

## 3 · Canvas Renders the Draft  (UI design-time)

Grey placeholders appear:

```
[CSV Loader] → [Loop Products] → [???] → [Aggregator]
```

Hovering nodes triggers Frosty suggestions (Pricing Strategy, Listing Agent, …). The user drags suggested blocks; Canvas auto-connects them.

---

## 4 · Draft ⇒ **Partial Blueprint** ⇒ **Blueprint**

Canvas persists each edit via MCP API (`PUT /blueprints/partial/{id}`). Edge-strict JSON schema rejects bad payloads.

`POST /blueprints/partial/{id}/finalize` converts to a validated **Blueprint**:

```jsonc
{
  "blueprint_id": "bp_99e8",
  "nodes": [ {"id": "load_csv", "type": "tool", "tool_name": "csv_loader", …}, … ],
  "metadata": {"owner": "alice"}
}
```

All design-time errors (missing deps, cycles) are blocked here.

---

## 5 · Compile-time – Registry Lookup & Manifest

`Workflow.from_blueprint()`
1. Resolves each `tool_name`/`agent_package` in the global registry.
2. Builds strict **NodeConfig** objects (edge validation).
3. Writes a frozen JSON manifest for GitOps/audit.

---

## 6 · Run-time Execution (lenient bus)

```
Workflow → NodeExecutor (retries/cache/timeout) → Unified Executors → Tool/Loop/LLM
```

* **NodeExecutor** enforces the node’s `input_schema`, handles retries & budgets.
* It passes a *rich* context dict into the executor.
* Executors allow `additionalProperties: true` so nodes can ignore unrelated keys.
* Outputs are validated **before** they re-enter the bus.

This "strict-edge / lenient-bus" pattern matches Airflow (XCom), Prefect (Results), Dagster (OpContext).

---

## 7 · Live Feedback

Each node emits `nodeStarted/nodeFinished` events via WebSocket; Canvas paints green ticks and Frosty summarises: *“9 listings succeeded, 0 failed.”*

---

## 8 · Iteration

User: “Frosty, change margin to 30 % and re-run only failed items.”

Frosty patches the Blueprint; Orchestrator executes incrementally; Canvas updates in real-time.

---

## 9 · Deployment

`POST /mcp/runs` launches the frozen blueprint in staging with `max_parallel=10`; GitOps records the manifest for audit.

---

### Why **Strict-Edge / Lenient-Bus** is Essential

| Layer | Validation | Reason |
|-------|------------|--------|
| REST / SDK / Blueprint | **Strict** (`additionalProperties=false`) | Governance, reproducibility, API contracts |
| Internal DAG Context | **Lenient** (kwargs, extras) | Composability, AI-generated nodes, future proofing |

This dual contract enables Frosty & Canvas to add or rearrange nodes without breaking downstream schemas while still guaranteeing deterministic deployment artefacts.

---

## Summary

The happy path demonstrates how a single natural-language idea flows through Draft → Canvas editing → Blueprint → compiled Workflow → runtime execution with live feedback, fulfilling the vision outlined in `frosty_canvas_vision_roadmap.md`.
