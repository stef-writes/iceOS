# Web-Search Content Pipeline Demo – **Discover → Analyze → Adapt → Publish**

_Last updated: 2025-06-20_

---

## 1. Purpose

Demonstrate how iceOS converts a single topic into platform-ready content by:
1. Discovering fresh sources (web search).
2. Browsing and extracting article text.
3. Analysing & summarising key insights.
4. Adding an original point-of-view.
5. Adapting the result into Tweets, a LinkedIn post and one or two blog drafts.

Throughout the run we exercise caching, retries, tracing and schema validation.

---

## 2. Audience

* Non-technical content creators who care about output, not internals.
* Internal engineers – the doc doubles as a checklist & regression-test spec.

---

## 3. High-Level Flow (6 Nodes)

| # | Node ID | Type | Description | Key Settings |
|---|---------|------|-------------|--------------|
| 1 | `discover_links` | ToolNode → `WebSearchTool` | Fetch top 10 fresh links for the topic. | `retries=1`, `use_cache=True` |
| 2 | `browse_pages`   | ToolNode → `BrowserTool`   | Download HTML & extract main text for each link. | `concurrency=4` |
| 3 | `analyze_content`| AiNode                  | Detect themes, facts & noteworthy stats across pages. | — |
| 4 | `aggregate_summary` | AiNode               | Produce 300-word executive summary with citations. | — |
| 5 | `author_angle`   | AiNode                  | Craft a unique "take" (original commentary). | `temperature=0.8` |
| 6 | `platform_adapter` | CompositeNode         | Generate 5 Tweets, 1 LinkedIn post, 1-2 blog drafts. | `output_schema` validation |

Graph view: `discover_links → browse_pages → analyze_content → aggregate_summary → author_angle → platform_adapter`.

---

## 4. Engine Features Exercised

1. **Per-node retry & backoff** – flaky HTTP in `discover_links` handled gracefully.
2. **Context isolation** – multiple creators can run demos concurrently.
3. **LRU output cache** – second run of same topic skips `discover_links`.
4. **Tracing** – each node emits a `node.execute` span with attrs `node_id`, `success`, `retry_count`.
5. **Schema validation** – every Ai node declares an `output_schema`; invalid outputs fail fast.

---

## 5. Deliverables

| Item | Path / Ref |
|------|------------|
| Workflow YAML | `examples/content_pipeline.yaml` |
| Regression test | `tests/demo/test_content_pipeline.py` |
| Demo script | `scripts/record_content_demo.sh` |
| Screencast | `/assets/demos/content_pipeline.mp4` |
| Observability screenshots | `/docs/images/jaeger_content_demo.png` |

---

## 6. Implementation Checklist

### 6.1 Tools & Nodes

- [ ] **BrowserTool**  
  - Location: `src/ice_sdk/tools/browser.py`  
  - Parameters: `url` (str).  
  - External call: HTTP GET; extract readable text via `trafilatura`.  
  - Caching: memoise for 24 h using `ice_sdk.cache.global_cache()`.  
  - Parallelism: async with `max_concurrency=4`.

- [ ] **platform_adapter** CompositeNode  
  - File: `examples/content_pipeline.yaml`.  
  - Contains 3 Ai sub-nodes (`twitter_adapter`, `linkedin_adapter`, `blog_adapter`).  
  - Each sub-node declares an `output_schema` from `schemas/social.py`.  
  - Shared prompt: _"You are a social media copywriter …"_.  
  - `temperature=0.7`, `max_tokens=300`.

- [ ] **schema models**  
  - File: `schemas/social.py`.  
  - Models: `TwitterPost`, `LinkedInPost`, `BlogPost`.  
  - Used for runtime validation and automatic docs generation.

### 6.2 Engine & API Gaps

- [ ] **BrowserTool sandbox** – prevent execution of 3rd-party JS, download HTML only.  
- [ ] **Observability compose** – add OTLP exporter to `docker-compose.observability.yml`; expose Jaeger at :16686.  
- [ ] **Docs** – write `docs/observability.md` incl. screenshot `docs/images/jaeger_content_demo.png`.

### 6.3 Quality Gates

- [ ] Unit test `tests/tools/test_browser.py` covers error handling & caching logic.  
- [ ] Integration test `tests/demo/test_content_pipeline.py` runs the 6-node chain with stubbed web requests and asserts cache hit on second run.  
- [ ] Update coverage threshold in `pyproject.toml` if LOC increases.

---

## 10. External Services & Secrets

| Purpose | Endpoint | Env Var(s) | Notes |
|---------|----------|------------|-------|
| Web search | SerpAPI | `SERPAPI_KEY` | required by `WebSearchTool`. |
| Tracing | Jaeger OTLP | `OTEL_EXPORTER_OTLP_ENDPOINT` | set by docker-compose. |

Set `ICE_TEST_MODE=1` during **all** automated tests to stub external calls.

---

## 11. Recommended Dev Workflow (≈1 day)

1. **Branch & scaffolding**  
   `git switch -c feat/content-pipeline` and create stub files/tests.
2. **BrowserTool**  
   Implement class → write unit test → `make test` passes.
3. **Composite workflow & schemas**  
   Write `schemas/social.py` models, `examples/content_pipeline.yaml` and prompts.
4. **Observability compose & docs**  
   Add OTLP exporter, document in `docs/observability.md`.
5. **Full integration test**  
   `tests/demo/test_content_pipeline.py` exercises LRU cache + retry.
6. **Polish & merge**  
   `make format lint test`, update coverage target, open PR.

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
| 1 | Browser tool & workflow YAML | Platform adapter & tests |
| 2 | Observability compose + docs | Polish & screencast |

---

## 9. Post-Demo Re-use

* Becomes a **template** in the future Tool Marketplace.
* Regression test protects against caching & isolation regressions.
* Screencast fuels marketing & onboarding material. 