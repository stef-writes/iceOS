# iceOS Naming Conventions – 2025-07-22

> “Strong names prevent weak architecture.”  – *iceOS Principle*
>
> This page is the **single source of truth** for how we talk about nodes, skills, agents, and workflows across every layer of iceOS.  Keep it in sync with code changes – stray vocabulary is treated as technical debt.

---

## 1. Why Naming Matters

1. **Static guarantees.**  Canonical strings (e.g. `llm`, `tool`) allow Pydantic & MyPy to reject invalid blueprints at build-time.
2. **Layer separation.**  Each layer (Core ⇄ SDK ⇄ Orchestrator ⇄ UI) has its own concerns; clear names avoid leaky abstractions.
3. **Extensibility.**  A stable vocabulary lets us add new capabilities (e.g. `evaluator`) without breaking old ones.

---

## 2. Canonical Runtime Node Types (v1.1)

| NodeType (Core enum) | Primary Purpose | Typical Payload Fields |
|----------------------|-----------------|------------------------|
| `tool`               | Call a deterministic **Tool** implementation once (pure function or side-effect). | `tool_name`, `tool_args`, `input_schema`, `timeout`, `retries` |
| `llm`                | Single-prompt **LLM Operator** (no planning). | `model`, `prompt`, `llm_config`, `temperature`, `max_tokens`, `tools` |
| `agent`              | Iterative reasoning loop; may call many tools; keeps memory & budget. | `package`, `config`, `toolbox`, `memory_cfg` |
| `condition`          | Boolean branch in the DAG. | `expression`, `true_branch`, `false_branch` |
| `nested_chain`       | Execute another workflow as a node. | `chain_spec` / `chain_id`, `exposed_outputs` |

*Anything else is an extension and **must not** collide with these keys.*

---

## 3. Cross-Layer Vocabulary Matrix (Layer ↔ Code ↔ JSON)

| Concern | Core Layer (ice_core) | SDK Layer (ice_sdk) | Design-time JSON | Example File/Class |
|---------|-----------------------|---------------------|------------------|--------------------|
| Deterministic execution | `NodeType.TOOL` | `SkillBase` subclass **(Tool)** | `{ "type": "tool" }` | `csv_reader_skill.py` |
| LLM wrapper | `NodeType.LLM` | `LLMOperator` | `{ "type": "llm" }` | `summariser_operator.py` |
| Autonomous agent | `NodeType.AGENT` | `AgentSkill` | `{ "type": "agent" }` | `smart_planner_agent.py` |
| Branching | `NodeType.CONDITION` | N/A (handled by orchestrator) | `{ "type": "condition" }` | — |
| Run sub-workflow | `NodeType.NESTED_CHAIN` | `ScriptChain` factory | `{ "type": "nested_chain" }` | `marketing_funnel_chain.py` |

> **Rule of thumb:**  *Tool* ⇄ *Skill*, *Agent* ⇄ specialised *Skill*, *Chain* ⇄ *Workflow*.

---

## 4. Key Distinctions

### 4.1 Tool vs. Skill (Design-time vs. Runtime)
* **Tool (design-time)** – JSON contract exposed to agents & UI (name, args, schema).
* **Skill (runtime implementation)** – Python class under `ice_sdk/tools/` (currently `skills/`) that fulfils a Tool node.
  *We are phasing out the word “Skill” in favour of “Tool implementation”.*

### 4.2 Agent vs. “LLM + Tools”
An **agent** is more than an LLM call; it:
1. Loops until a goal is reached or a budget is exhausted.
2. Chooses which tools to call at each step.
3. Maintains private scratch-pad memory.

Using `llm` + `tool` nodes can *approximate* simple agents, but true iterative reasoning belongs in an `agent` node.

### 4.3 NestedChain vs. Workflow
A **workflow** is always top-level; a **nested_chain** is a workflow embedded *inside* another.  Treat nested chains as black boxes with defined inputs/outputs.

### 4.4 Condition Node vs. If-logic Inside a Skill
Use a `condition` node when the **workflow topology** changes based on runtime data.  Embed an `if` in a Skill only for local parameter tweaks.

---

## 5. Deprecation & Alias Policy

| Deprecated Alias | Canonical | First Warned | Hard Fail | Removal |
|------------------|-----------|--------------|-----------|---------|
| `ai`             | `llm`     | v1.0-beta    | **Removed** (v1.1) | — |
| `prebuilt`       | `agent`   | v1.0-beta    | **Removed** (v1.1) | — |
| `skill`          | `tool`    | v1.0-beta    | **Warn** (v1.1) | v1.2 |
| `subdag`         | `nested_chain` | v1.0-beta | **Removed** (v1.1) | — |

Any occurrence of these aliases in a blueprint now raises `ValueError` during conversion and fails CI.

---

## 6. Registry & Executor Cheat Sheet

| Concern | Registry Symbol | Module Path |
|---------|-----------------|-------------|
| Tools (deterministic) | `global_tool_registry` | `ice_sdk.registry.tool` |
| LLM Operators | `global_operator_registry`<br/>(alias `global_processor_registry` – deprecated) | `ice_sdk.registry.operator` |
| Executor map | `NODE_REGISTRY` | `ice_sdk.registry.node` |
| Agents | `global_agent_registry` | `ice_sdk.registry.agent` |

`ai_executor` has been renamed **`llm_executor`**. The old symbol is kept with `@deprecated` until v1.2.

---

## 7. Migration Checklist (2025-07-22)

1. Rename `global_skill_registry` → `global_tool_registry`.
2. Introduce `global_operator_registry` and move LLMOperator registrations.
3. Duplicate `ai_executor` logic into `llm_executor`; mark old name deprecated.
4. Delete concrete `*_skill.py` files replaced by operators; leave stub shim with `@deprecated`.
5. Search-replace variable names `_chain_skills` → `_chain_nodes` or `_chain_tools`.
6. Update CI linter to block new imports of deprecated aliases.

> **Status:** checklist tracked in project TODOs.

---

## 8. Code & JSON Examples

```jsonc
// Minimal LLM node
{
  "id": "summarise",
  "type": "llm",
  "model": "gpt-4o",
  "prompt": "Summarise rows: {{rows}}",
  "temperature": 0.3,
  "max_tokens": 256,
  "llm_config": {"provider": "openai"}
}
```

```python
# Deterministic Skill implementation
from ice_sdk.skills.base import SkillBase

class CsvSumSkill(SkillBase):
    """Return the sum of a numeric CSV column."""

    async def execute(self, *, path: str, column: str) -> float:  # type: ignore[override]
        import pandas as pd
        return pd.read_csv(path)[column].sum()
```

```jsonc
// Wrap the above skill as a Tool node
{
  "id": "sum",
  "type": "tool",
  "tool_name": "csv_sum_skill",
  "tool_args": {"path": "input.csv", "column": "price"}
}
```

---

## 7. Extending the Taxonomy

1. Prototype in **SDK**: subclass `SkillBase`; set `node_subtype` in `Meta`.
2. Prove demand; if orchestration needs special handling, propose a new **NodeType** in Core.
3. Update this document & the Node Charter before merging.

---

_Last updated: 2025-07-22_ 

---

## 9. Definition of “Done” for Naming Alignment Migration

A PR may claim the naming refactor is *done* **only** when every item below is true **and enforced by CI**.

1. **Registries & Executors**
   - `global_tool_registry`, `global_operator_registry`, and `NODE_REGISTRY` are the **only** runtime registries.
   - All `llm` nodes are executed by `llm_executor`; `ai_executor` exists solely as a deprecated alias and is **never** imported by project code or tests.
   - `global_skill_registry`, `global_processor_registry` **were removed in v1.1**; importing them now raises `ImportError`.
   - `global_agent_registry` is the **only** agent registry.

2. **Source Tree & Naming**
   - Deterministic implementations live in `ice_sdk/tools/`.  No file ends with `_skill.py`; that suffix was removed in v1.1.
   - LLM operators live in `ice_sdk/llm/operators/`.
   - Variable names like `_chain_skills`, `chain_skills` have been replaced by `_chain_tools` or `_chain_nodes`.

3. **Blueprint & API-level**
   - `NodeSpec.type` accepts only the canonical strings from §2. Any alias (`ai`, `skill`, `prebuilt`, `subdag`) raises `ValueError` in `convert_node_spec` and fails CI.
   - All example blueprints under `examples/` validate without deprecation warnings.

4. **Documentation & Lint**
   - This document remains accurate after code changes.
   - `scripts/ci/check_aliases.py` (or equivalent) blocks new usages of deprecated symbols and aliases.

5. **Tests & CI Gates**
   - `pytest` passes with ≥90 % coverage on changed lines.
   - `mypy --strict` passes.
   - Pre-commit hooks and GitHub Actions succeed on `main`.

Only when **all five categories** are satisfied—automated and human-reviewed—may the checklist in §7 be marked *complete* and the naming alignment ticket closed. 