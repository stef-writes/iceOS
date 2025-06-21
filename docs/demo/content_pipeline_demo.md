# Content Pipeline Demo – **Curate → Adapt → Publish**
# Content Pipeline Demo – **Discover → Analyze → Adapt → Publish**
# Content Pipeline Demo – **Discover → Analyze → Adapt → Publish**

_Last updated: 2025-06-19_

---

## 1. Purpose

Show a non-technical content creator how iceOS turns a raw topic into a multi-platform "content pack" in one click, while exercising every recent hardening feature (retries, caching, session isolation, tracing, safe-mode tools).

---

## 2. Audience

* Creative professionals and stakeholders unfamiliar with the engine internals.
* Internal developers – this doc doubles as an implementation checklist & regression-test spec.

---

## 3. High-Level Flow (7 Nodes)

| # | Node ID | Type | Description | Key Settings |
|---|---------|------|-------------|--------------|
| 1 | `discover_links` | ToolNode → `WebSearchTool` | Fetch top 10 fresh links for the topic. | `retries=1`, `use_cache=True` |
| 2 | `browse_pages` | ToolNode → `BrowserTool` | Download HTML, extract title & main text for each link. | `concurrency=4` |
| 3 | `analyze_content` | AiNode | Detect common themes and interesting stats across pages. | — |
| 4 | `aggregate_summary` | AiNode | Produce 300-word executive summary of findings. | — |
| 5 | `author_angle` | AiNode | Write our unique point-of-view & key take-aways. | `temperature=0.8` |
| 6 | `platform_adapter` | CompositeNode | Generate channel-specific content (Tweets ×5, LinkedIn post, 1-2 Blog drafts). | Each sub-node has `output_schema` validation |

Graph view: `discover_links → browse_pages → analyze_content → aggregate_summary → author_angle → platform_adapter`.

---

## 4. Engine Features Exercised

1. **Per-node retry & backoff** – flaky HTTP in `discover_links` handled gracefully.
2. **Context isolation** – multiple creators can run demos concurrently.
3. **LRU output cache** – second run of same topic hits cache in node 1.
4. **Tracing** – each node produces `node.execute` span with attrs `node_id`, `success`, `retry_count`.
5. **Safe-mode tools** – `hero_assets` & `live_post` execute only when API request sets `trust_level="trusted"`.
6. **Schema validation** – every Ai node declares an `output_schema`; invalid outputs fail fast.

---

## 5. Deliverables

| Item | Path / Ref |
|------|------------|
| Workflow YAML | `examples/platform_adapt.yaml` |
| Regression test | `tests/demo/test_platform_adapt.py` |
| Demo script | `scripts/record_content_demo.sh` |
| Screencast | `/assets/demos/content_pipeline.mp4` |
| Observability screenshots | `/docs/images/jaeger_content_demo.png` |

---

## 6. Implementation Checklist

### 6.1 Tools & Nodes

- [ ] **BrowserTool**  
  - Location: `src/ice_sdk/tools/browser.py`  
  - Parameters: `url` (str).  
  - External call: HTTP GET to fetch page; use `trafilatura` to extract readable text.  
  - Caching: memoise responses for 24 h using `ice_sdk.cache.global_cache()`.  
  - Supports parallel execution with `max_concurrency=4`.

- [ ] **platform_adapter** CompositeNode  
  - File: `examples/platform_adapt.yaml`.  
  - Contains 3 Ai sub-nodes (`twitter_adapter`, `linkedin_adapter`, `blog_adapter`).  
  - Each sub-node declares `output_schema` pointing to models in `schemas/social.py` (see §6.2).  
  - Shared prompt fragment: _"You are a social media copywriter …"_.  
  - `temperature=0.7`, `max_tokens=300`.

- [ ] **schema models**  
  - File: `schemas/social.py`.  
  - `class TwitterPost(BaseModel)`, `LinkedInPost`, `BlogPost`.  
  - Used for runtime validation and docs generation.

### 6.2 Engine & API Gaps

- [ ] **Safe-mode guard** — FastAPI route `POST /v1/workflows/{id}/execute` returns **HTTP 403** if request header `X-Trust-Level != "trusted"` AND any node/tool declares `requires_trust=True`.  
- [ ] **Observability compose** — Add OTLP exporter to `docker-compose.observability.yml`; expose Jaeger at :16686.  
- [ ] **Docs** — write `docs/observability.md` including screenshot `docs/images/jaeger_content_demo.png`.

### 6.3 Quality Gates

- [ ] Unit tests: `tests/tools/test_unsplash.py`, `tests/tools/test_social_poster.py` cover happy path, retry path, trust-level rejection.  
- [ ] Integration test `tests/demo/test_platform_adapt.py` runs the full 7-node chain against stubbed APIs and asserts cache hit on second run.  
- [ ] Unit tests: `tests/tools/test_browser.py` cover error handling & caching logic.  
- [ ] Integration test `tests/demo/test_content_pipeline.py` runs the full 6-node chain against stubbed Web & asserts cache hit on second run.  
- [ ] Update coverage threshold in `pyproject.toml` if LOC increases.

---

## 10. External Services & Secrets

| Purpose | Endpoint | Env Var(s) | Notes |
|---------|----------|------------|-------|
| Web search | SerpAPI | `SERPAPI_KEY` | already used by `WebSearchTool`. |
| Image search | Unsplash | `UNSPLASH_ACCESS_KEY` | public access key is enough. |
| Social posting | Buffer API | `BUFFER_ACCESS_TOKEN` | optional — demo works without live posting. |
| Tracing | Jaeger OTLP | `OTEL_EXPORTER_OTLP_ENDPOINT` | set by docker-compose.

Set `ICE_TEST_MODE=1` during **all** automated tests to stub external calls.

---

## 11. Recommended Dev Workflow (≈1 day)

1. **Branch & scaffolding**  
   `git switch -c feat/unsplash-social-tools` and create stub files/tests.
2. **UnsplashSearchTool**  
   Implement class → write unit test → pass `make test`.
3. **SocialPosterTool**  
   Implement with Buffer API stub → write tests.
4. **Composite workflow & schemas**  
   Write `schemas/social.py` models, `examples/platform_adapt.yaml` and basic prompts.
1. **Branch & scaffolding**  
   `git switch -c feat/content-pipeline` and create stub files/tests.
2. **BrowserTool**  
   Implement class → write unit test → pass `make test`.
3. **Composite workflow & schemas**  
   Write `schemas/social.py` models, `examples/content_pipeline.yaml` and prompts.
5. **Safe-mode FastAPI guard**  
   Enforce `X-Trust-Level` header, add tests for 200 vs 403.
6. **Observability compose & docs**  
   Add OTLP exporter, document in `docs/observability.md`.
7. **Full integration test**  
   `tests/demo/test_content_pipeline.py` exercises LRU cache + retry.
8. **Polish & merge**  
   `make format lint test`, update coverage target, open PR.

_Use `UNSPLASH_ACCESS_KEY` and `SERPAPI_KEY` locally; Buffer token only if you plan to actually publish._

---

## 7. Running the Demo Locally

```bash
# 1. Spin up tracing backend & dependencies
$ docker compose -f docker-compose.observability.yml up -d

# 2. Execute the workflow
$ make demo CONTENT_TOPIC="Urban beekeeping" TRUST_LEVEL=trusted

# 3. View traces at http://localhost:16686 (Jaeger UI)
```

Re-run the command to observe cache hits (node 1 will be skipped; trace shows <1 ms duration).

---

## 8. Timeline to Demo-Ready (≈1½ days)

| Day | Morning | Afternoon |
|-----|---------|-----------|
| 1 | Safe-mode guard & Unsplash tool | SocialPoster tool & workflow YAML | 
| 2 | Observability compose + docs | Tests, polish & screencast |

---

## 9. Post-Demo Re-use

* Example becomes a **template** in the future Tool Marketplace.
* Regression test protects against regressions in caching, context isolation & safe-mode.
* Screencast feeds marketing & onboarding materials. 