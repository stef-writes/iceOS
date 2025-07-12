# ☃ iceOS “Launch 0” – Condensed Release Road-map  
(Everything you need to put a real product in front of first-wave users, nothing more.)

## Guiding rule
Ship the thinnest vertical slice that proves:  
1. deterministic, type-safe execution;  
2. vectors & DB work end-to-end;  
3. a non-technical user can drag a flow and hit **Run**.

---

## 0 Prep (week 0)
• Lock scope, freeze non-critical PRs.  
• Create `release/launch-0` branch.

---

## 1 Backend Core (weeks 1-3)

| Deliverable | From which doc? | Why now? |
|-------------|-----------------|----------|
| `HybridEmbedder` + Chroma adapter, SHA-256 hasher | Vector Indexing | Other layers depend on it for search, RAG, dedup. |
| `SqlTool`, `NoSqlTool`, `SchemaValidatorTool` | Database Strategy P1 | Enables *deterministic* data ops inside early chains. |
| Metrics: token & wall-time per node | Front-end Roadmap P3 | Needed for upcoming dashboard. |

*Exit test* → CLI chain that embeds → stores in Chroma → simple SQL read passes `make test`.

---

## 2 Official-Extra “Hello World” Tools (week 4)

* We ship a **separate pip package** – e.g. `ice-tools-slack` – that contains
  the Slack adapter, plus an updated `ice-tools-http` for generic REST.
* Core repo remains vendor-free; plugin discovery picks the extra up
  automatically.
* Each extra follows the same rules (typed I/O, validate(), 90 % coverage).

*Exit test* → `pip install ice-tools-slack` then a chain posts to Slack + hits public API.

---

## 3 Front-End Phase 0 + 1 (weeks 4-7)

| Item | Why |
|------|-----|
| Storybook + Tailwind/Radix tokens | Shared design language. |
| React-Flow canvas (nodes, edges, basic zoom/pan) | Minimal drag-and-drop. |
| TOML ⇄ Canvas codec + inline pydantic errors | Lets PM build simple 3-node chain. |

Defer: project sidebar, virtualised big-graph handling.

*Exit test* → Non-dev user creates `embed→sql→slack` chain in browser, clicks **Save**, CI passes.

---

## 4 One-Click Local Deploy (week 8)

* CLI `ice-cli deploy docker`  
* Uvicorn container with `/run/{chain}` REST route.  
* Secrets via `.env`; no cloud yet.

*Exit test* → `docker run …` returns JSON result for saved chain.

---

## 5 Run Dashboard α (weeks 9-10)

* Simple timeline view (start/end, status colour).  
* Cost panel (aggregate tokens + ms).  
* Log tail.

Tech: SSE from backend; React table.

*Exit test* → failing node highlighted within 15 s; metrics render.

---

## 6 Public Beta Hardening (weeks 11-12)

• Add Fly.io deploy wizard (reuse Docker image).  
• AES-GCM secret storage.  
• Cron picker (single schedule per chain).  
• Docs quick-start + screencast.

---

## Nice-to-Have (post-beta / not launch-blocking)

1. Vector alt-index adapters (`Annoy`, `HNSW`).  
2. DB “ExplainPlan” & “IndexAdvisor” tools.  
3. Template gallery & marketplace.  
4. Marketplace publishing workflow.  
5. WCAG-AA polish, Lighthouse ≥ 90.

---

## Timeline snapshot

```
wk 0   | prep
wk 1-3 | Core vectors + DB tools
wk 4   | Slack + HTTP tools
wk 4-7 | Canvas MVP
wk 8   | Docker deploy
wk 9-10| Run dashboard α
wk 11-12| Fly deploy + cron + docs → Public Beta
```

---

## Anything overkill?

• Full multi-tenant “ice_cloud” control-plane → **defer** (need only Fly wizard now).  
• Marketplace, RBAC, advanced access logs → **post-beta**.  
• HNSW & MinHash semantic dedup → **ship later** once basic Chroma path is proven.

---

### Launch definition of done
1. A PM can build & run a 3-step flow (embed → vector search → Slack) without writing Python.  
2. The same flow can be deployed to Fly.io in < 5 min.  
3. Dashboard shows run duration & cost; failing nodes visible.  
4. All repo rules still green: mypy --strict, ≥ 90 % coverage, ci/tests pass.

☑ Ship it.