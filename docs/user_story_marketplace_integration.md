# User Story – Marketplace Integration via iceOS

**Persona:** Lisa, Backend Engineer at BlueWave Commerce

---

## Context & Problem
Lisa must let merchants bulk-publish enriched product listings to Facebook Shops (Shopify coming later).  Existing enrichment stops at CSV parsing – there’s no validated, reusable way to create correct Graph-API calls or to test them safely.

Pain-points:
* Ad-hoc scripts hard-code HTTP requests.
* Errors surface only at runtime – no design-time validation.
* Formatting + network logic are tangled, making tests brittle.

---

## Why iceOS Solves It
| Need                           | iceOS Feature                                               |
|--------------------------------|-------------------------------------------------------------|
| Declarative steps              | Node/Tool models                                            |
| Early validation               | MCP `/components/validate` (schema + runtime)               |
| Fast scaffolding               | `ice-cli scaffold tool`                                      |
| Safe local testing             | Mock FastAPI router + test-mode tools                       |
| Production-grade execution     | Orchestrator DAG engine (retries, sandbox, metrics)         |

---

## Activities (Happy Path)
1. **Discover tools** – `ice-cli list tools`  
2. **Scaffold formatter** – `ice-cli scaffold tool facebook_formatter`  
3. **Implement pure transform** – no network
4. **Register via MCP** – `curl /api/v1/components/validate` with the tool JSON
5. **Scaffold generic poster** – `ice-cli scaffold tool api_poster`
6. **Register poster the same way**
7. **Add mock router** – `/api/v1/mock/marketplace/items`  
8. **Build workflow (DSL)** – load CSV → loop → formatter → poster
9. **Validate** – `workflow.validate()`
10. **Execute locally** – `workflow.execute()` (posts to mock router)
11. **Verify** – `GET /api/v1/mock/marketplace/items` shows Facebook-ready JSON
12. **Promote to prod** – switch `mock=false`, real URL & headers
13. **Docs generated** – MkDocs picks up tool docstrings
14. **CI gates** – `make test`, `make type`, coverage ≥55 %

---

## Notes / TBD
* CLI scaffolder creates boilerplate; Lisa edits docstring + `execute()`.
* `api_poster` input schema: `url`, `payload`, `headers`, `auth`, `mock`.
* Mock router lives in `ice_api/api/mock_marketplace.py`.
* Exact CLI upload step uses `ice-cli export tool ... | curl .../validate`.

This document serves as a reference flow; implementation details may evolve.
