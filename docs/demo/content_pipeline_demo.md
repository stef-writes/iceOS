# Content Pipeline Demo – **Curate → Adapt → Publish**

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
| 1 | `discover_links` | ToolNode → `WebSearchTool` | Fetch top 8 fresh links for the topic. | `retries=1`, `use_cache=True` |
| 2 | `curate_summaries` | AiNode | Summarise each link ≤60 words, add relevance score 1-5. | — |
| 3 | `hero_assets` | ToolNode → `UnsplashSearchTool` | Retrieve image URLs for the most relevant links. | `requires_trust=True` |
| 4 | `platform_adapter` | CompositeNode | Generate channel-specific content (Twitter, LinkedIn, Instagram, Blog). | Each sub-node has `output_schema` validation |
| 5 | `post_plan` | AiNode | Build JSON schedule (platform, timestamp, content_id). | — |
| 6 | `live_post` | ToolNode → `SocialPosterTool` | Optionally publish according to schedule. | `requires_trust=True` |
| 7 | `package_content` | ToolNode | Zip all artefacts into a downloadable archive. | — |

Graph view: `discover_links → curate_summaries → hero_assets → platform_adapter → post_plan → live_post → package_content`.

---

## 4. Engine Features Exercised

1. **Per-node retry & backoff** – flaky HTTP in `discover_links` handled gracefully.
2. **Context isolation** – multiple creators can run demos concurrently.
3. **LRU output cache** – second run of same topic hits cache in node 1.
4. **Tracing** – each node produces `node.execute` span with attrs `node_id`, `success`, `retry_count`.
5. **Safe-mode tools** – `hero_assets` & `live_post` execute only when API request sets `trust_level="trusted"`.

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

- [ ] Implement `UnsplashSearchTool` (requires_trust=True).
- [ ] Implement `SocialPosterTool` (requires_trust=True, side-effect posting disabled in tests).
- [ ] Add `CompositeNode` YAML for `platform_adapter` with four Ai sub-nodes.

### 6.2 Engine & API Gaps

- [ ] Finish FastAPI safe-mode guard (HTTP 403 on untrusted calls).
- [ ] Add OTLP exporter config to `docker-compose.observability.yml`.
- [ ] Write `docs/observability.md` walk-through referencing this demo.

### 6.3 Quality Gates

- [ ] Unit tests for new tools + retry, cache and trust-level paths.
- [ ] Integration test `tests/demo/test_platform_adapt.py` runs the full chain against stubbed external APIs.
- [ ] Update coverage target if lines increase.

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