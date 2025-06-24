# iceOS — Competitive Landscape & "Text-to-Flow" Action Plan  
*Last updated: 2025-06-24*

---

## 0. Purpose
This document complements `vision_and_moats.md` by:

* Mapping **where iceOS fits** versus Workflow86, LangGraph and n8n (incl. AI Chrome extensions).
* Capturing the **capability gaps** that matter for adoption (chiefly natural-language authoring).
* Providing a **concrete, engineering-ready action plan** for closing those gaps in the next two sprints.

The doc lives in `docs/` so that roadmap and competitive signals stay version-controlled alongside code.  Update it at the end of every sprint or when a competitor ships a materially new feature.

---

## 1. Market Snapshot (June-2025)

| Dimension | Workflow86 | LangGraph | n8n (+AI ext.) | **iceOS (0.2-alpha)** |
|-----------|------------|-----------|----------------|-----------------------|
| Licence / deploy | Closed-source SaaS | MIT, library | AGPL core + cloud | Apache-2 OSS |
| Primary UX | Chat → visual canvas | Code (Python/TS) | Visual canvas, side-panel chat | Code (Pydantic) |
| **Text→flow maturity** | GA – describe or upload diagram | DIY | GA via extension (JSON injection) | **Not yet (planned "Frosty Copilot")** |
| Target workflows | Business Ops w/ forms & tasks | Multi-agent LLM graphs | API/data automations | Agentic + event-driven AI |
| Guard-rails | Version-controlled runs, human approval | Build your own | Basic retries | Depth / token / semantic hooks |
| Extensibility | JavaScript/Python code node | Any Python callable | 400+ nodes | Python tools; CLI auto-reg soon |

---

## 2. iceOS Current State

We already ship:

* **Async Orchestrator** – `ScriptChain` with level-parallel execution, caching, guard-rails and metrics.
* **Type-safe SDK** – Pydantic configs, import-linter contracts, 56 % test coverage.
* **Service Layer** – FastAPI endpoints for executing a node or chain.
* **LLM Adapters** – OpenAI, Anthropic, Gemini, DeepSeek.

**Missing for parity with "text-to-flow" incumbents**

| Gap | Impact | Owner | Status |
|-----|--------|-------|--------|
| Natural-language **Planner** that converts a prompt → `WorkflowSpec` | Core usability | Platform team | ─ |
| **Verifier** agent to lint the spec (types, loops, guard policy) | Safety & DX | Platform team | ─ |
| CLI / REST surface (`ice plan …`) | Developer loop | DX team | ─ |
| Minimal web **Copilot** panel in FastAPI | Wider adoption | Front-end | ─ |

---

## 3. Action Plan — close the gap in < 3 weeks

### 3.1 Work-breakdown

| # | Deliverable | Est. | Notes |
|---|-------------|-----|-------|
| 1 | Prompt-→-`IceWorkflowSpec` **Planner** (few-shot + JSON schema) | 3–4 d | Leverage existing `LLMService`.
| 2 | `ice plan` CLI wrapper + watch-mode | 1.5 d | Re-use CLI scaffolding from week-2 milestone.
| 3 | JSON **Verifier** (schema + depth/token checks) | 2 d | Hook into guard util modules.
| 4 | REST endpoint `POST /v1/workflows/generate` | 0.5 d | Serialization is already in place.
| 5 | **Frosty Copilot** HTMX/React side-panel (MVP) | 3 d | Static assets served by FastAPI.
| 6 | Docs + demo GIF + blog post | 1 d | Drives adoption.
| 7 | **CapabilityRegistry + `ice search` CLI** | 1.5 d | Exposes existing *CapabilityCard*s, enables planner reuse. |
| **Total** | **≈ 13.5 dev-days** | Two 1-week sprints (Registry can slip to Sprint B if needed). |

### 3.2 Sprint sequencing (assuming 2-week cadence)

*Sprint A*  
Day 1-2  Planner PoC → internal demo  
Day 3    Verifier skeleton + integrated CLI (`ice plan`)  
Day 4    Wire CLI to REST + tests  
Day 5    Code-freeze ➜ tag `v0.3.0-beta`

*Sprint B*  
Day 1-2  Copilot UI (HTMX)  
Day 3    End-to-end polish & edge-cases  
Day 4    Docs, sample video, tweet-storm  
Day 5    Release `v0.3.0`, update this doc

### 3.3 Success KPIs

* "`ice plan` hello-world" ≤ **12 s** on M2 laptop.  
* ≥ 90 % of generated DAGs pass Verifier on first shot.  
* Demo PR merged by at least **2 external contributors** within 4 weeks.  
* Project GitHub stars **+30 %** MoM after launch tweet.

---

## 4. Update Protocol

1. **During sprint:** keep the *Action Plan* table in sync with issue numbers and PR links.
2. **Sprint retro:** bump dates, move completed items to "Shipped" subsection.
3. **Competitor ships** a relevant feature → create a short "Market event" entry and reassess priority.

---

## 5. Appendix — quick glossary

* **Planner** – LLM call that outputs a list of `NodeConfig` JSON objects.
* **Verifier** – Synchronous function (or small agent) that validates planner output against schema + guard rules.
* **Copilot** – Thin front-end that lets users chat / iterate; **not** the full marketplace UI. 