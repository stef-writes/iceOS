# iceOS Vision & Roadmap (v1 – June 2025)

*This document replaces the draft from 2024-Q4.*

---

## 1 · Why We Exist

> *“Give every distributed team a shared canvas where natural-language ideas become governance-ready AI workflows in seconds.”*

Today, building an AI workflow still feels like writing infrastructure code: YAML
pipes, API keys, observability glue.  iceOS removes that friction by
combining three super-powers:

1. **Intelligent Canvas** — describe intent in plain English; the canvas
   sketches a Workflow, cost/latency estimates, and data contracts.
2. **Deterministic Runtime** — the same blueprint that visualises on the
   canvas runs in prod with strict budget & safety guarantees.
3. **Team Memory** — meetings, decisions and telemetry are captured and tied
   to the exact graph version that was deployed.


## 2 · Product Pillars

| Pillar | “Jobs-to-be-done” | Success Metric |
| ------ | ----------------- | -------------- |
| **Zero-Code Design** | PM can draft a classifier → notifier workflow without YAML | 1 minute P50 draft time |
| **Governed Execution** | FinOps trusts costs will not exceed $X per run | 0 budget overruns per month |
| **Collaborative Canvas** | Remote team co-edits, sees live costs, leaves comments | ≥3 active users / session |
| **Continuous Improvement** | Frosty agent surfaces optimisations from real traces | 15% cost or latency gain / suggestion |


## 3 · Hero User Stories

### US-01 · Solo Prototyper
> *“As a solo founder I type ‘summarise new Zendesk tickets into Slack’, get a ready-to-run pipeline and can deploy it in <5 minutes.”*

### US-02 · Distributed Team Design Session
> *“As a team we jump on a call, drag nodes, and Frosty updates cost metrics live while discussion is transcribed into context.”*

### US-03 · Governance Officer
> *“I need auditable traces & cost caps; iceOS enforces budgets and shows a run ledger without extra config.”*

### US-04 · Marketplace Contributor (Phase 3)
> *“I publish a ‘DeepL Translate’ tool; other teams can drag-drop it and revenue-share automatically.”*


## 4 · YC-Style Phased Roadmap

| Stage | Timeline | *Creator WOW* Moment (placeholder) | KPI Gate | Target Users |
| ----- | -------- | ---------------------------------- | -------- | ------------ |
| **B0 – Alpha Solo** | Jun → Aug 2025 | *“🪄 Blank prompt → runnable chain in <60 s”* | P50 draft < 1 min | 10 indie hackers |
| **B1 – Private Beta Teams** | Sep → Nov 2025 | *“🧑‍🤝‍🧑 Live co-edit canvas w/ realtime cost overlay”* | ≥3 users/session | 3 design-partners |
| **B2 – Public Beta** | Dec 2025 → Feb 2026 | *“🚀 One-click deploy & share link”* | 100 WAT teams | solo & small teams |
| **B3 – Marketplace** | Mar → Jun 2026 | *“🛒 Add paid ‘___’ node from marketplace”* | $10k GMV / mo | 200 tool authors |
| **B4 – Enterprise GA** | H2 2026 | *“🔒 Drag SSO / audit module into graph”* | ≥3 F500 pilots | enterprise buyers |

> **Note**: Signature WOW moments are placeholders.  At each gate we will pick the most market-aligned feature (e.g. *Deep-Wiki autogen* for B3 if that is the hottest meme).

### Milestone Framework

For every phase we document:

* **Key Functions** – core capabilities unlocked in this phase
* **Integrations** – external APIs / vendors introduced
* **Creator Activities** – what a solo maker can now do end-to-end

**B0 Example**

*Key Functions*
* Natural-language → blueprint parser  
* Local ScriptChain executor

*Integrations*
* OpenAI GPT-4o (prompt parsing)

*Creator Activities*
* Draft + run a “fetch RSS → summarise → email” chain locally without code

Repeat the same template for subsequent phases when scoping work.

**Demo Checkpoints** (every 4 weeks)
1. Generate & execute simple chain (B0-W4)
2. Cost heat-map & guardrails (B0-W8)
3. Canvas co-edit + voice transcript (B1-W4)
4. Frosty optimisation loop (B1-W8)
5. SaaS billing & quotas (B2-W4)
6. Marketplace tool publish (B3-W4)


## 5 · Execution Plan (next 90 days)

| Week | Deliverable | Owner |
| ---- | ----------- | ----- |
| 1 | Thin FastAPI wrapper around `ScriptChain.execute` | BE Lead |
| 3 | NL→Chain POC with 4 builtin tools | ML Engineer |
| 5 | Canvas drag-drop prototype (React + Mermaid) | FE Lead |
| 6 | Frosty prompts for node mapping | PM / ML |
| 8 | In-memory BudgetEnforcer + SSE telemetry | BE Lead |
| 10 | Alpha onboarding docs & CLI scaffolder | DevEx |
| 12 | **Demo Day MVP** – US-01 end-to-end | Entire team |

Risks: vendor LLM pricing volatility, browser WebRTC scaling, compliance for PII.
Mitigations: provider abstraction, fallback to text-only collab, early SOC-2 prep.


## 6 · North-Star Metrics

1. **Blueprint Draft → Deploy Time** (goal < 5 min P50)
2. **Weekly Active Teams** (WAT)
3. **Cost Savings Suggested by Frosty** (℅ of total spend)
4. **Marketplace GMV**


## 7 · Key Architectural Bets

* MCP (Model Context Protocol) as the sole contract between design & runtime
* Context Store abstraction for **MeetingContext** & **GraphContext**
* Deterministic DAG runner with strict retries & budget enforcement
* Plugin registry for nodes & tools (enables marketplace stage)

### 7.1 · Design Decisions & Rationale

| ID | Decision | Rationale | Trade-offs |
|----|----------|-----------|-----------|
| **A-1** | **MCP as the only contract between design & runtime** | Loose coupling → each layer can ship independently; enables 3rd-party design tools | Versioning overhead; need backward-compat bridges |
| **A-2** | **`src/` vs `services/` layout** | Keeps importable code discoverable by tooling; deployables remain obvious | Slightly longer import paths for API code |
| **A-3** | **Context Store abstraction** | Same API for `MeetingContext`, `GraphContext`, future `UserContext`; swap Redis ↔ Postgres | Additional interface layer |
| **A-4** | **Deterministic DAG runner** | Reproducibility & auditability; avoids hidden async side-effects | Harder to support truly dynamic graphs (will revisit in B3) |
| **A-5** | **BudgetEnforcer baked into executor** | Cost governance by default; FinOps friendly | Might limit exotic pricing schemes; can be bypassed via flags if needed |
| **A-6** | **Plugin registry & marketplace** | Enables ecosystem & revenue share; decouples node/tool lifecycle | Needs strong vetting & version pinning |
| **A-7** | **MeetingContext captured via transcript + canvas diff** | Creates unique training corpus for Frosty suggestions | Compliance concerns (PII); mitigated via redaction pipeline |
| **A-8** | **Fallback to vendor media stack (LiveKit)** | Time-to-market > reinventing SFU; SLA covers scale | Vendor lock-in risk; long-term plan to abstract via WebRTC adapter |

These decisions are revisited quarterly by the architecture council and logged as ADRs under `docs/adr/`.

---

> **Maintainers**: Update after each phase exit.  Last updated 2025-06-15. 