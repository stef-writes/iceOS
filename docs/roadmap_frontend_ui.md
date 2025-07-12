# iceOS Front-End & UX Roadmap  
*Last updated <2025-05-XX>*  

## Purpose  
Give the engineering, design and product teams a single source-of-truth for all user-facing goals — from a “Figma-like” canvas to live dashboards and one-click deployment.  Each phase lists:  
* Scope & rationale  
* Key deliverables  
* Ownership / dependencies  
* Success criteria  
* Risks / mitigations  

---

## Phase 0 “Foundations & Quick Wins” (0 – 2 wks)

| Theme | Deliverable | Owner(s) | Notes |
|-------|-------------|----------|-------|
| Design system | Choose CSS/TS stack (Tailwind + Radix UI) & create Storybook of primitives | Design + FE | Use existing brand tokens; must export to React/MDX |
| Dev-ex | Vite + PNPM mono-repo config under `src/ice_ui/` | FE | TS strict mode; ESLint + Prettier integrated |
| Docs | “Front-end contributing” page | DevRel | How to run Storybook, tests, type-check |

**Success** → GitHub Actions build passes for `ice_ui` unit tests + Storybook preview.

---

## Phase 1 “Visual Builder MVP” (2 – 8 wks)

### Scope & Rationale  
Non-engineers need a drag-and-drop canvas to create/edit `chains.toml` without touching VS Code.

### Key Deliverables  
1. **Canvas core** • React Flow  + Zustand store.  
2. **Node palette auto-generated** from `/ice_sdk/node_registry.py` via REST (`/nodes/registry`).  
3. **TOML ⇄ Canvas codec** • Round-trip must be lossless (`assert codec(canvas) == codec^-1(toml)`).  
4. **Inline validation** • Display pydantic/parsing errors next to offending node/edge.  
5. **File / Project sidebar** • CRUD for multiple flows.  
6. **Export** button writes back to repo or prompts `ice-cli pull`.

### Success Criteria  
* Build a 5-node flow entirely in UI, click **Save**, repo gains syntactically correct `chains.toml` passing `make test`.  
* 90th-percentile time-to-first-flow ≤ 4 minutes for a “PM” persona in user test.

### Risks / Mitigations  
* **Perf on big chains** → virtualise node list; throttle change events.  
* **Registry drift** → nightly CI job regenerates JSON schema used by UI.

---

## Phase 2 “One-Click Deploy” (4 – 6 wks, overlaps P1 late)

### Deliverables  
1. **Deploy modal** (fly.io & Docker to start).  
2. **Secrets manager** UI – AES-GCM local encryption, stored server-side.  
3. **Live status badge** showing container health.  
4. **Generated REST & WS endpoints** display with copy-to-clipboard.  

### Success  
* Fresh repo → “Deploy to Fly” wizard → HTTPS endpoint responds within 5 minutes, no terminal usage.  

---

## Phase 3 “Run Dashboard & Visual Debugger” (6 – 10 wks)

### Deliverables  
| Feature | Detail |
|---------|--------|
| Timeline view | Bars per node (start, duration, status colour) fed from `metrics.node_start/end/error` SSE |
| Cost panel | Aggregate tokens, $ & wall-clock per run + per node |
| Log panel | Stdout/structured log stream, filterable by node id |
| Re-run button | Replays the chain with same inputs, drops to detail diff view |

### Success  
* Users can locate a failing node & view its last inputs/outputs in ≤ 15 s.  
* 100 % of `metrics.py` events render with no client console errors.

---

## Phase 4 “Scheduler & Triggers” (2 – 4 wks)

* Cron expression picker (Quartz).  
* Webhook & email triggers (HTTP POST, IMAP idle).  
* History list with next/previous run calculation.

---

## Phase 5 “Template Gallery & Marketplace” (backlog)

* Browse, search, one-click clone of open-source flows.  
* Publisher workflow with automated lint/mypy/coverage check.  
* Rating + download metrics.

---

## Cross-Cutting Constraints & Governance

1. **Layer boundaries**  
   * `ice_ui` may **import** from `ice_sdk` / `ice_app` but never vice-versa.  
2. **Side-effects** remain in Tool layer; UI triggers deployments via API, not direct SDK calls.  
3. **Type safety**  
   * TS `strictNullChecks` on UI, Python `--strict` remains mandatory.  
4. **Accessibility**  
   * WCAG AA: colour contrast, keyboard nav, ARIA labels tested via Playwright + axe.  
5. **Performance budgets**  
   * Initial JS bundle ≤ 250 kB gzipped.  
   * Canvas drag latency ≤ 16 ms (60 fps) on 100-node graph.  
6. **Security**  
   * All secrets encrypted at rest, never echoed to logs.  
   * CSP headers, `helmet` middleware on dashboard HTTP server.  
7. **CI gates**  
   * FE tests (Vitest + Playwright), Storybook snapshots, Lighthouse perf audits.  
8. **Official Extras**  
   * High-demand vendor adapters (Slack, Gmail, etc.) ship as **pip extras** like `ice-tools-slack`; core stays vendor-free.  
   * UI shows install badge when a chain references a tool that lives in an extra package.

---

## Appendix A Dependency Matrix

| Package | Purpose | License | Pin Strategy |
|---------|---------|---------|--------------|
| React Flow | Graph canvas | MIT | Exact version in `package.json`, Renovate PRs |
| TailwindCSS | Styling | MIT | ^major, locked by PNPM |
| Radix UI | Accessible primitives | MIT | ^major |
| Zustand | State | MIT | ^major |
| Vite | Build | MIT | Follow vite-major |
| ice-tools-slack | Official extra – Slack adapter | Apache-2 | Separate package; semantic-ver w/ own deps |
| ice-tools-http | Official extra – generic REST | Apache-2 | Separate package |

---

## Appendix B User-Flow Cheat-Sheet

1. **Create project** → GitHub template / CLI.  
2. **Open canvas** → `/ui/#/my-flow`  
3. Drag nodes, connect edges → auto-validate.  
4. Hit **Deploy** → choose Fly.io region, add secrets.  
5. Watch first run in **Dashboard**; debug if necessary.  
6. Press **Schedule** → daily at 09:00 UTC.  
7. Browse **Costs** weekly; iterate on prompts/embedding.

---

> **REMEMBER** : All new UX must uphold existing repo rules (side-effects in Tools, pinned deps, mypy strict, ≥ 90 % coverage).  If a feature can’t meet the bar, open an Architecture Decision Record instead of sneaking around it.
