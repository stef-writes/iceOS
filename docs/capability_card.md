# Capability Card — Comprehensive Requirements Document

*Hybrid "LinkedIn-profile + baseball-card" view for Agents, Tools, Nodes, Chains, Flows, …*

---

## 1  Purpose & Scope

| Item             | Detail                                                                                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Goal**         | Provide a single, consistent UI+API representation ("Capability Card") for every executable or discoverable unit in the Agent-ICE platform.                        |
| **Targets**      | `agent`, `tool`, `node`, `chain`, `flow` (and future kinds: dashboards, datasets, etc.).                                                                           |
| **Deliverables** | ① Back-end catalog schema & endpoints, ② React/Tailwind card component, ③ Interaction behaviours (flip, compare, drag-to-canvas), ④ Monitoring & versioning hooks. |
| **Out-of-scope** | Building new runtime features (scheduler, executor); this doc only covers representation & discovery.                                                              |

---

## 2  Stakeholders

| Role                      | Needs                                                             |
| ------------------------- | ----------------------------------------------------------------- |
| **Low-code end user**     | Quick visual understanding, trust signals, one-click "Run/Use".   |
| **Developer**             | Fast discovery, schema inspection, drag-and-drop into blueprints. |
| **LLM / Agent**           | Machine-readable JSON for planning & reasoning.                   |
| **SRE / Ops**             | Metrics, version, ownership, policy compliance at a glance.       |
| **Security / Governance** | RBAC tags, guard-rail indicators, audit trail.                    |

---

## 3  Definitions

* Capability Catalog: Registry service that exposes metadata for all capability kinds.
* Capability Card: Visual & JSON manifestation of a single catalog entry.
* Hero section: Brief textual description + primary CTA.
* Core-stats strip: Compact KPIs (latency, cost, success %).

---

## 4  High-Level Requirements

### 4.1 Functional

| ID       | Requirement                                                                                                         |
| -------- | ------------------------------------------------------------------------------------------------------------------- |
| **F-1**  | Catalog **MUST** expose a REST endpoint `GET /catalog/:kind/:id` returning the canonical Card JSON.                 |
| **F-2**  | Endpoint **MUST** respond in ≤ 150 ms @ p95 for cached entries.                                                     |
| **F-3**  | Front-end **MUST** render a responsive Card component with header, hero, stat strip, badges, owner links.           |
| **F-4**  | Card **MUST** flip (hover/click) to reveal extended stats, changelog, governance section.                           |
| **F-5**  | Card **MUST** support drag-and-drop onto the blueprint canvas -> emits a `createNode` event with pre-filled config. |
| **F-6**  | User **MUST** be able to select ≥2 cards and open **Compare Mode** (radar / table).                                 |
| **F-7**  | Search box + filter chips **MUST** allow filtering by kind, tag, owner, freshness, cost tier.                       |
| **F-8**  | Version drift (installed vs latest) **MUST** trigger inline upgrade banner with CTA.                                |
| **F-9**  | LLM-callable **Capability Catalog Tool** **MUST** return paginated JSON slices conforming to schema §7.             |
| **F-10** | RBAC: users only see cards they are authorised to run or view.                                                      |
| **F-11** | All card views **MUST** be keyboard navigable and screen-reader friendly (WCAG AA).                                 |

### 4.2 Non-Functional

| Category                 | Target                                                                            |
| ------------------------ | --------------------------------------------------------------------------------- |
| **Performance**          | 95th-percentile card API ≤ 150 ms / 15 KiB payload.                               |
| **Scalability**          | 1 M catalog entries; 1 k concurrent UI clients.                                   |
| **Reliability**          | 99.9 % uptime; cached read replicas.                                              |
| **Security**             | OAuth2-bearer; field-level redaction for sensitive stats.                         |
| **Observability**        | OTel traces for `catalog.fetch`, metric labels (`kind`, `id`).                    |
| **Extensibility**        | Adding a new `kind` requires only schema file + entry-point; no core code change. |
| **Internationalisation** | Display fields translatable via i18n keys; fallback to English.                   |

---

## 5  User Stories (selected)

| ID  | As a …           | I want …                                            | So that …                           |
| --- | ---------------- | --------------------------------------------------- | ----------------------------------- |
| U-1 | Low-code user    | to skim a Tool card and hit **Run**                 | I can test without reading docs.    |
| U-2 | Blueprint author | to drag a Node card onto canvas                     | I can compose a workflow visually.  |
| U-3 | SRE              | to flip a Chain card and view last-run stats        | I can diagnose errors quickly.      |
| U-4 | Frosty agent     | to call `catalog.list(kind="tool", tag="pii-safe")` | I plan with policy-compliant tools. |

---

## 6  Detailed Functional Specification

### 6.1 Card Data Model

```jsonc
{
  "kind": "tool",          // enum
  "id": "sql.query",       // unique
  "display_name": "SQL Query Runner",
  "tagline": "Parameterized SQL against JDBC DBs",
  "description": "...",    // ≤ 280 chars
  "stats": {
    "mean_latency_ms": 235,
    "cost_per_call_usd": 0.0002,
    "success_rate_pct": 99.4,
    "last_updated": "2025-06-08T14:22:05Z",
    "version": "1.3.4"
  },
  "badges": ["JDBC", "PII-safe", "stable"],
  "owner": {
    "name": "Data Platform",
    "avatar_url": "https://...",
    "contact": "@datateam"
  },
  "links": {
    "docs": "/docs/tools/sql-query",
    "repo": "https://github.com/…",
    "run": "/run/tool/sql.query"
  },
  "governance": {
    "rbac": ["data_reader"],
    "policies": ["token_budget_medium"],
    "guard_rails": ["pii_scrub_v2"]
  },
  "metrics_ref": "otel:tool.sql.query",   // join key for metrics backend
  "schema": { /* JSON-Schema or OpenAPI fragment */ }
}
```

### 6.2 API Endpoints

| Verb   | Route                    | Params                                | Result                         |
| ------ | ------------------------ | ------------------------------------- | ------------------------------ |
| `GET`  | `/catalog`               | `?kind, tag, owner, q, limit, cursor` | List slice (paginated)         |
| `GET`  | `/catalog/{kind}/{id}`   | -                                     | Single Card JSON               |
| `POST` | `/catalog/compare`       | body: `[{"kind":"tool","id":"..."}]`  | Aggregated stat JSON for radar |
| `GET`  | `/catalog/schema/{kind}` | -                                     | JSON-Schema definition         |

### 6.3 Front-End Component Props (TypeScript)

```ts
type CapabilityCardProps = {
  data: CapabilityCard;       // matches JSON above
  size?: "sm" | "md" | "lg";
  onDragStart?: () => void;
  onCTA?: () => void;         // Run / Inspect
  highlightUpgrade?: boolean; // version drift
};
```

### 6.4 Interaction Flow: Drag-to-Canvas

1. User drags card → `dragstart` emits `{kind,id}`.
2. Canvas receives → fetches `/catalog/{kind}/{id}` if not cached.
3. Canvas creates provisional node with pre-populated config (`schema.default`).
4. User can open config modal for fine tuning.

---

## 7  Data Storage & Caching

| Layer             | Tech               | Purpose                             |
| ----------------- | ------------------ | ----------------------------------- |
| **Primary store** | PostgreSQL (jsonb) | Authoritative catalog rows.         |
| **Cache**         | Redis/LRU 5 min    | Low-latency lookup for hot cards.   |
| **Metrics store** | Prometheus         | Stats aggregated per `metrics_ref`. |

---

## 8  Security & RBAC

* Catalog queries pass user JWT → service maps to scopes.
* Card fields tagged `sensitive` (e.g., cost) are redacted if caller lacks `stats.read`.
* Drag-to-canvas blocked if user lacks `execute` on that capability.

---

## 9  Observability

| Signal         | Detail                                                                          |
| -------------- | ------------------------------------------------------------------------------- |
| **Trace span** | `catalog.fetch` → attributes: `kind`, `id`, `status`.                           |
| **Metrics**    | `catalog_request_latency_ms{kind}` histogram; `ui_card_render_ms` in front-end. |
| **Logs**       | Structured JSON with request-id linking UI ⇄ API ⇄ DB.                          |

---

## 10  Acceptance Criteria (Definition of Done)

1. API returns card JSON matching schema; validated via OpenAPI tests.
2. Front-end renders card grid; Chrome Lighthouse score ≥ 90 (perf + a11y).
3. Drag-and-drop creates executable node that passes DependencyGraph validation.
4. Compare Mode shows radar with latency, cost, success% for 2+ cards.
5. Metrics dashboards display p95 latency & error rate for catalog service.
6. Security tests confirm RBAC enforcement & field redaction.

---

## 11  Milestone Timeline (2-Sprint Execution)

| Sprint | Deliverables                                                      |
| ------ | ----------------------------------------------------------------- |
| **S1** | DB schema, CRUD API, basic React Card, list & detail pages.       |
| **S2** | Flip & Compare interactions, drag-to-canvas, RBAC, metrics, docs. |

---

## 12  Constraints & Assumptions

* Must coexist with existing FastAPI back-end & React/Tailwind front-end stack.
* All new code under `ice_sdk/catalog` (back-end) and `ui/components/CapabilityCard`.
* Icons via Lucide; no proprietary font licenses.
* Initial catalog population handled by plug-in registration hooks on service start-up.

---

## 13  Risks & Mitigations

| Risk                                  | Impact            | Mitigation                                                      |
| ------------------------------------- | ----------------- | --------------------------------------------------------------- |
| Latency spikes on large list queries  | Poor UX           | Pagination + Redis cache + indexed columns, p95 SLA monitoring  |
| Version drift causing silent failures | Inconsistent runs | Upgrade banner + optional auto-migration hook                   |
| Schema evolution breaking agents      | LLM failures      | Semantic-version card schema; deprecate with dual-format window |

---

## 14  Open Issues

1. Finalise visual design tokens per `kind` colour palette.
2. Decide whether extended stats live in same API or separate `/stats` endpoint.
3. Determine multi-tenant segregation strategy (separate DB schema vs row-level).

---

### ✅ Next Action

*Confirm this requirements draft or annotate changes; once approved we'll create user-stories + tickets for Sprint 1.* 