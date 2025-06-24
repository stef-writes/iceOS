### iceOS Chain Pre-Implementation Checklist

> Fill out **every** section before you start coding. Keep the completed file in `docs/design/` (one per chain).

---

#### 1. Project Information
- **Chain name:** <!-- _Human-readable name_ -->
- **Version / Revision:** <!-- e.g. v0.1 draft -->
- **Author(s):** <!-- Your GitHub handle(s) -->
- **Date:** <!-- YYYY-MM-DD -->

#### 2. Use-Case Summary
- **Problem statement:**
  <!-- What pain-point does this solve? -->
- **Target users / personas:**
- **Desired "wow" outcome:**

#### 3. Inputs & Outputs
| Item | Details |
| --- | --- |
| Primary user input(s) | <!-- fields, file, URL, etc. --> |
| Additional context | <!-- from GraphContext, previous runs → yes/no --> |
| Expected final output | <!-- JSON, Markdown, etc. --> |
| Success criteria | <!-- measurable; e.g. <2 USD/run & ROUGE-L > 0.3 --> |

#### 4. High-Level Data-Flow
```
# ASCII or mermaid sketch
# NodeA --> NodeB --> NodeC
```
- **Total nodes planned:** <!-- target 12–15 -->
- **Failure policy:** <!-- HALT | CONTINUE_POSSIBLE | ALWAYS -->

#### 5. Node Inventory
| ID | Type (ai/tool/agent) | Purpose / Prompt summary | Model / Tool | Dependencies | Output keys |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

_Add rows until all nodes are listed._

#### 6. Tool & API Requirements
| Name | Built-in? | External endpoint | Auth / ENV var | Rate limits | Example call |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

#### 7. Context & Memory
- **GraphContext usage:** <!-- short-term only? persistent memory? -->
- **Data privacy considerations:** <!-- PII, compliance -->

#### 8. Error Handling & Retries
- **Node-level timeouts:**
- **Retry strategy:** <!-- exponential backoff, etc. -->
- **Fallback nodes:** <!-- IDs or N/A -->

#### 9. Testing Plan
- **Unit tests to add:**
- **Mock strategy for external APIs:**
- **Acceptance / E2E scenarios:**

#### 10. Environment & Dependencies
- **Required ENV vars:** `OPENAI_API_KEY`, …
- **New Python packages:** <!-- pin versions -->

#### 11. Repository Impact
- **New code files / paths:**
- **Docs to update:**

#### 12. KPIs & Observability
| Metric | Target | Collection method |
| --- | --- | --- |
| Avg. latency |  |  |
| Cost / run |  |  |
| Error rate |  |  |

#### 13. Compliance Check (✓ = done)
- [ ] Uses Pydantic models & type-hints for every new node/tool
- [ ] No `app.*` imports inside `ice_sdk.*`
- [ ] All external side-effects only within Tool implementations
- [ ] Async/await used for I/O
- [ ] Tests updated in `tests/` and `make test` passes

#### 14. Sign-Off
| Role | Name | Date | Approved? |
| --- | --- | --- | --- |
| Author |  |  |  |
| Reviewer |  |  |  |

---
**Save this file alongside the chain code before submitting a PR.** 