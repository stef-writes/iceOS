# Database Strategy — Unified Tool-Led Architecture (v3.0.0)

> **Status:** Draft — Pending Architecture Council Review (2025-07-10)
> **Champion:** iceOS CTO  
> **Supersedes:** v2.1.0 (tool/agent split clarified; roadmap updated)

---

## 1  Purpose & Context

iceOS treats every database interaction as a **deterministic function**.  This guarantees auditability and replay while still allowing large-language-model (LLM) agents to *plan* complex, multi-step workflows.

```
┌───────────────┐   simple read/insert   ┌───────────────────┐
│ ScriptChain   │ ─────────────────────▶ │ SqlTool / …       │
│ (determinism) │                       │ (deterministic)    │
└───────────────┘                       └───────────────────┘
      ▲   ▲                                    │
      │   │ complex tasks                      ▼
      │   └──────────────────────────────┐ ┌───────────────┐
      │                                  ▼ │ DbOptimizer   │
      │                                 (ai node → tools) │
      └───────────────────────────────────┘ └───────────────┘
```

*Simple CRUD* → direct Tool Nodes.  *Schema design, cost tuning* → AiNode with an allow-listed tool set.

---

## 2  Guiding Principles

1. **Determinism First** – All DB logic executes inside `BaseTool` subclasses.  Results are cacheable and replayable.  
2. **LLM-Planner Second** – Agents (`DbArchitectAgent`, `DbOptimizerAgent`, …) *compose* tools; they never embed side-effects.  
3. **Adapter Pattern** – Tools wrap drivers; swapping Postgres ⇆ Snowflake changes *one* file, never a chain.  
4. **Schema as Contract** – JSON-Schema validates every payload pre- and post-execution (Rule 3 & 13).  
5. **Cost Governance** – `BudgetEnforcer` guards every tool call; routers can downgrade to cheaper replicas automatically.

---

## 3  Runtime Layering

```mermaid
graph TD
    subgraph Tool_Layer
        SQL["SqlTool"] --▶ VAL["SchemaValidatorTool"]
        NoSQL["NoSqlTool"] --▶ VAL
        EXP["ExplainPlanTool"]
        IDX["IndexAdvisorTool"]
    end

    subgraph Agent_Layer
        OPT["DbOptimizerAgent"] --▶ EXP
        OPT --▶ IDX
        ARCH["DbArchitectAgent"] --▶ SQL
    end

    USER["User / App"] --simple--> SQL
    USER --complex--> OPT
    VAL --schemas--> REG[/schema_registry/]
    OPT --budget--> BUDGET[BudgetEnforcer]
```

---

## 4  Deterministic Tool Catalogue (Phase 1)

| Tool | Purpose | Key Params |
|------|---------|------------|
| `SqlTool` | Execute parameterised SQL | `query`, `dialect`, `params?` |
| `NoSqlTool` | CRUD for document stores | `action`, `collection`, `payload` |
| `SchemaValidatorTool` | Validate result/DDL against domain schema | `schema_id` |
| `ExplainPlanTool` | Return cost & plan for a query | `query`, `dialect` |
| `IndexAdvisorTool` | Suggest indexes from plan/workload | `table`, `query_samples` |

All inherit from `BaseTool`, expose JSON-Schema via `parameters_schema`, and call `BudgetEnforcer.register_tool_execution()`.

---

## 5  LLM Agents (Phase 2)

| Agent | Responsibility | `allowed_tools` |
|-------|----------------|-----------------|
| `DbArchitectAgent` | Green-field schema design | `SqlTool`, `SchemaValidatorTool` |
| `DbOptimizerAgent` | Iteratively lower cost/latency | `ExplainPlanTool`, `IndexAdvisorTool`, `SqlTool` |
| `DbAgent` | Cross-DB join, federation, migration orchestration | *all above* |

Agents derive from `AiNodeConfig` → executed by `AgentNode`, which already supports tool-calling loops, retries & cycle detection.

---

## 6  ScriptChain Patterns

### 6.1  Pure Tool Flow (deterministic)

```yaml
id: customer-crud-v1
nodes:
  - id: insert_order
    type: tool
    tool_name: SqlTool
    tool_args:
      query: |
        INSERT INTO orders (id, customer_id, total) VALUES (:id, :cust, :total);
      dialect: postgres
      params: {id: 123, cust: 7, total: 42.0}
```

### 6.2  Agent-Planner Flow

```yaml
id: optimise-order-query
nodes:
  - id: plan
    type: ai
    model: gpt-4o
    prompt: ${optimise_prompt}
    allowed_tools: [ExplainPlanTool, IndexAdvisorTool, SqlTool]

  - id: final_query
    type: tool
    tool_name: SqlTool
    tool_args:
      query: ${plan.optimised_sql}
      dialect: postgres
```

The chain remains replayable because every tool invocation + agent decision is logged.

---

## 7  Governance & Observability

| Concern | Mechanism |
|---------|-----------|
| Budget | `BudgetEnforcer` in every tool’s `run()` |
| Schema Drift | `SchemaValidatorTool` + CI drift tests |
| PII | Future `DBGuardrailTool` before data egress |
| Latency SLOs | Cold/Hot replica router (Phase 2) |

All tools emit `NodeExecutionResult` → standard node spans feed dashboards and alerts.

---

## 8  Roadmap

| Phase | Target | Deliverables | Exit Gate |
|-------|--------|--------------|-----------|
| **1 Core Tools** | Q3-2025 | `SqlTool`, `NoSqlTool`, `SchemaValidatorTool` | Contract tests green; overhead ≤ 5 ms |
| **2 Planner APIs** | Q4-2025 | `ExplainPlanTool`, `IndexAdvisorTool`, router | ≥ 30 % cost reduction on ref workload |
| **3 Agent Layer** | Q1-2026 | `DbArchitectAgent`, `DbOptimizerAgent`, cross-DB executor | 95 % plan success (CI) |
| **4 Domain Packs** | Q2-2026 | Finance & Healthcare schema packs | 3 design partners validated |

---

## 9  Reference Interfaces

```python
from typing import Literal
from ice_sdk.tools.base import BaseTool
from ice_sdk.models import TableResult
from ice_sdk.providers import BudgetEnforcer
from ice_sdk.utils.validation import validate

class SqlTool(BaseTool):
    """Execute parameterised SQL deterministically."""

    name = "SqlTool"
    description = "Execute parameterised SQL safely."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query":   {"type": "string"},
            "dialect": {"enum": ["postgres", "snowflake", "bigquery"]},
            "params":  {"type": "object"},
        },
        "required": ["query", "dialect"],
    }

    @validate  # Rule 13
    async def run(
        self,
        query: str,
        dialect: Literal["postgres", "snowflake", "bigquery"],
        params: dict | None = None,
    ) -> TableResult:
        BudgetEnforcer().register_tool_execution()
        # driver dispatch …
        ...
```

---

## 10  Decision Log

1. **Kept Tool-first approach** — Maintains determinism for 80 % of workloads.  
2. **Rejected agent-only design** — Benchmarks show 3× latency for CRUD.  
3. **Adopted JSON-Schema contracts** — Required for audit & SOC-2.  
4. **Adapter drivers** — Avoid vendor lock-in.  
5. **Schema drift tests in CI** — Ensure prod ≡ staging.

---

> *“Database interactions should feel like any other function call — with an LLM whispering the best plan when you need it.”*  
> — iceOS Architecture Council 