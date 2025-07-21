# Naming Conventions & Conceptual Map

> “Strong names prevent weak architecture.”  – _iceOS Principle_

This document captures **why** we picked the current vocabulary (Node, Skill, Agent, Chain …) and how to apply it consistently across SDK, orchestrator and UI layers.

---

## 1. Core Vocabulary

| Term | Layer | One-line Definition |
|------|-------|---------------------|
| **Node** | Core | Smallest executable unit in a workflow DAG. Expressed as `NodeConfig` JSON. |
| **Skill** | SDK | A concrete behaviour that can satisfy a Node at runtime (`SkillBase`). |
| **Agent** | SDK | _Specialised_ Skill that maintains memory / tool-use. Implemented via `AgentSkill` (subclass of `SkillBase`). |
| **LLM Operator** | SDK | Skill that wraps a direct LLM call with prompt template + parsing. |
| **Chain** | Orchestrator | Composition of Nodes; can itself be wrapped as a `NestedChainConfig` Node. |

### 1.1 Why “Agent = Skill”

1. **Single execution contract** – Orchestrator only needs one call-site (`await skill.execute()`).  Agents fulfil that without new engine hooks.
2. **Re-use** – Retry logic, circuit-breakers, cost tracking already live in `SkillBase`.
3. **Recursion** – An Agent may *use other skills/agents* as tools. Treating it as a Skill keeps the recursion graph uniform.
4. **Minimal core** – No extra Core node type → fewer breaking changes.

> Think of **Skill** as “_thing that can be executed_” and **AgentSkill** as “_thing that can think then execute_.”

---

## 2. Naming Rules

1. **Classes**
   * `SomethingSkill` – any direct `SkillBase` subclass.
   * `SomethingAgent` or `FooAgentSkill` – autonomous agent built on `AgentSkill`.
   * `XYZOperator` – LLM wrapper (inherits `SkillBase`).
2. **Files & Modules**
   * Place Skills in `ice_sdk/skills/<domain>/` (e.g. `web/facebook_marketplace_skill.py`).
   * Agents live in the same tree but should import **only** SDK-level helpers to keep layer boundaries.
3. **Registry Keys** (public names)
   * Lower-snake-case: `facebook_marketplace_agent`, `web_search_skill`.
   * Unique across the global registry.
4. **Metadata (`Meta` inner class)**
   ```python
   class FacebookMarketplaceAgent(AgentSkill):
       class Meta:
           node_subtype = "agent"
           commercializable = True
           license = "MIT"
   ```
5. **Node JSON**
   ```json
   {
     "type": "skill",
     "name": "facebook_marketplace_agent",
     "parameters": { "system_prompt": "…" }
   }
   ```

---

## 3. Extending the Taxonomy

Need a new runtime concept (e.g. _Evaluator_, _Guardrail_)?

1. **Prototype in SDK** – subclass `SkillBase`; use `node_subtype = "evaluator"`.
2. **Gather usage** – if multiple workflows depend on it **and** the subtype needs dedicated fields, promote a typed `EvaluatorParams` model.
3. **Last resort** – introduce a **new Core NodeType** only when the orchestrator itself must treat it differently.

---

## 4. FAQ

**Q : Can an Agent call another Agent?**  
A : Yes. Agents resolve tools via `global_skill_registry`, so treating Agents as Skills enables arbitrarily deep delegation trees.

**Q : Does this block resale/marketplace later?**  
A : No. `SkillMeta.commercializable` and future packaging utilities cover monetisation without touching Core.

---

## 5. Quick Reference Cheat-Sheet

```
Node            →  abstract payload in workflow JSON
Skill           →  runtime implementation in ice_sdk
AgentSkill      →  Skill with planning + memory
LLMOperator     →  Skill wrapping an LLM call
Chain           →  collection of Nodes (may recurse)
```

Keep this page updated whenever the vocabulary evolves. 