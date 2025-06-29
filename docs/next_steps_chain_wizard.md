# Interactive Chain Wizard – Implementation Roadmap

> Status: **Planned** (target release `v0.2.0`)

This document captures the design blueprint and incremental milestones for the
`ice sdk create-chain --wizard` feature.

---

## 1  Architecture Layers

| Layer | Responsibility | Notes |
|-------|----------------|-------|
| **IO layer** | Renders questions / collects answers (CLI prompts today, UI or agent later) | Typer + Questionary for v0.  Copilot will swap this layer. |
| **Wizard-Engine** | Stateless state-machine that emits **Question → Answer** cycles and finally a `WizardDraft` | Lives in `ice_cli.wizard.engine` (pure Python, no UI deps). |
| **Template layer** | Converts `WizardDraft` → concrete `NodeConfig` objects + `ScriptChain` Python scaffold | Re-uses existing template helpers. |

---

## 2  Question Catalogue (v0)

1. **Chain meta**  
   • name  
   • persist_interm_outputs (y/N)
2. **Node loop** (repeats)  
   • node_type (ai / tool / agent)  
   • node_name / id  
   • dependencies (multi-select)  
   • type-specific extras (model & prompt, tool ref, agent instructions …)  
   • advanced (retries, timeout, cache)
3. **Review**  
   • Render Mermaid graph + summary table  
   • Confirm → write files / run / exit

---

## 3  Milestones

| Milestone | Scope | ETA |
|-----------|-------|-----|
| **M0** | Linear graphs, `ai` + `tool` nodes, up to 10 nodes, writes `.chain.py`. | 1 week |
| **M1** | Mermaid graph preview, validation (dup IDs, cycles). | +3 days |
| **M2** | Wizard-Engine REST façade for Copilot, CLI remains a thin client. | +1 week |
| **M3** | Branching, `condition` & `sink` nodes, import existing YAMLs. | +2 weeks |

---

## 4  Copilot Integration Ideas

* Copilot feeds answers programmatically via REST, enabling natural-language flow authoring.
* Live cost estimation + policy checks surfaced during the Q&A loop.

---

## 5  Technical Notes

* Draft state stored in memory (JSON), serialisable to `draft_chain.yaml`.
* Node IDs auto-slugify names + numeric suffix.
* Engine unit-tested independent of UI via scripted answer sequences.

---

_Last updated: {{ build_date }} by `Cursor AI`_ 