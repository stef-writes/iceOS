# Starter Capability Library — Requirements Document

*(Minimal—but powerful—set of Nodes, Tools, Chains and Event Sources that every Agent-ICE deployment should ship out-of-the-box)*

---

## 1  Purpose & Scope

| Item                | Detail                                                                                                                                                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Goal**            | Provide a **factory-installed "starter kit"** of the most commonly-requested building blocks so users can compose useful automations on day 1.                                                                        |
| **What's included** | • 6 Core **Tools**<br>• 4 Foundational **Node** classes (wrappers around those tools + generic AiNode)<br>• 3 **Event Sources** (external triggers)<br>• 3 Reusable **Chains** that illustrate best-practice patterns |
| **Out-of-scope**    | Niche domain tools (e.g. biomedical NLP), UI widgets (covered elsewhere).                                                                                                                                             |

---

## 2  Stakeholders

* **Low-code users** — need working primitives without writing code.
* **Dev-rel / DX** — need examples that showcase extension points.
* **Frosty / other agents** — need deterministic utilities for planning.
* **SRE** — want observable, well-guarded defaults.

---

## 3  High-Level Feature List

| Category          | ID           | Capability                                               | Why it's in the starter kit                            |
| ----------------- | ------------ | -------------------------------------------------------- | ------------------------------------------------------ |
| **Tools**         | T-HTTP       | **HTTP Call Tool**                                       | Universal "fetch data" primitive (REST / GraphQL).     |
|                   | T-SQL        | **SQL Query Tool**                                       | 80 % of business data lives in DBs.                    |
|                   | T-RAG        | **Doc-Search Tool** (vector search)                      | Retrieval step for summarise, Q&A.                    |
|                   | T-CODE       | **Code-Search Tool**                                     | Frosty uses it for self-reflection / repo lookup.      |
|                   | T-FUNC       | **Python Function Tool**                                 | Rapid prototyping of pure Python transforms.           |
|                   | T-NATS       | **NATS Publish / Subscribe Tool**                        | Lightweight message bus connector.                     |
| **Nodes**         | N-AI         | **Generic AiNode** (already exists)                      | Calls any LLM provider.                                |
|                   | N-Tool       | **ToolNode** (generic wrapper, exists)                   | Executes any T-*.                                     |
|                   | N-Webhook    | **Webhook Source Node**                                  | Materialises inbound HTTP POST payload as node output. |
|                   | N-MQ         | **Message-Queue Source Node**                            | Consumes Kafka/NATS/Redis streams.                     |
| **Event Sources** | ES-Webhook   | **/events/webhook** FastAPI endpoint → EventDispatcher   | Immediate external triggers (Zapier, Stripe, GitHub).  |
|                   | ES-MQ        | **Async consumer** for Kafka/NATS/Redis                  | High-throughput, decoupled event ingestion.            |
|                   | ES-Scheduler | **Cron trigger** (time-based)                            | Scheduled workflows (nightly ETL, weekly report).      |
| **Chains**        | C-ETL-Δ      | **Delta-ETL Chain**: Webhook → SQL→ Ai summary           | Shows ingest-process-summarise pattern.                |
|                   | C-RAG-Q&A   | **Ask Documents Chain**: Doc-Search → Ai answer          | Canonical RAG pattern, used by Frosty.                 |
|                   | C-Repair     | **Self-Repair Chain**: Node error → Code-Search → Ai fix | Demonstrates auto-healing.                             |

---

## 4  Detailed Functional Requirements

### 4.1 Core Tools

| ID         | Interface (Pydantic `parameters` schema)                              | Output                                   | Key Constraints                                             |
| ---------- | --------------------------------------------------------------------- | ---------------------------------------- | ----------------------------------------------------------- |
| **T-HTTP** | `{ "method": "GET\|POST\|PUT\|DELETE", "url": "https://…", "headers": {str:str}, "body": str\|dict\|null, "timeout_s": int=30 }` | `{ "status": int, "headers": {...}, "body": str\|bytes }` | • Supports JSON & form-encoded<br>• Retries (3×, exp backoff)<br>• Circuit-breaker integrated |
| **T-SQL**  | `{ "connection_uri": "postgresql://…", "query": str, "params": list\|dict\|null, "fetch": "one\|many\|none" }` | `list[dict]`                   | • Param binding via DB driver<br>• PII-safe redaction option |
| **T-RAG**  | `{ "index_name": str, "query": str, "top_k": int=3 }`                 | `list[{ "chunk": str, "score": float }]` | • Works with pgvector & Weaviate<br>• Returns embedding ids |
| **T-CODE** | `{ "search_terms": str, "top_k": int=5 }`                             | `list[{ "path": str, "snippet": str }]`  | • Uses repo embedding store                                 |
| **T-FUNC** | `{ "python": str, "inputs": dict }`                                   | `Any JSON-serialisable`                  | • Sandboxed; time-limit 5 s                                 |
| **T-NATS** | `{ "server": str, "subject": str, "payload": Any }`                   | `{ "ack": bool }`                        | • Async pub/sub mode                                        |

*All tools expose their JSON-Schema via `get_parameters_json_schema()` and register under the entry-point group "ice.tools".*

---

### 4.2 Source Nodes

#### N-Webhook

* **Kind**: `"webhook"`
* **Lifecycle**: waits until `EventDispatcher` receives `"webhook/{route}"` event.
* **Output schema**: arbitrary JSON payload delivered in POST body.
* **Security**: HMAC SHA-256 signature header; shared secret stored in Vault.

---

### 4.3 Reusable Chains

| Chain ID       | Graph Sketch                                                                              | Notes                                                    |
| -------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| **C-ETL-Δ**    | Webhook → Tool(SQL insert) → Tool(SQL delta query) → AiNode(summary) → Tool(NATS publish) | Live ingestion + delta change detect + summary push.     |
| **C-RAG-Q&A** | Tool(RAG search) → AiNode(answer)                                                         | Parameterised to any index - serves as Frosty sub-chain. |
| **C-Repair**   | NodeError event → Tool(Code-Search) → AiNode(generate patch) → Tool(Git PR)               | Demonstrates self-healing pattern; uses GitHub API.      |

*Chains ship as YAML/JSON `ScriptChainDefinition` objects; users can clone and tweak.*

---

## 5  Cross-Cutting Technical Requirements

| Area                    | Requirement                                                                                          |
| ----------------------- | ---------------------------------------------------------------------------------------------------- |
| **Observability**       | Every Tool & Node MUST emit OTel span (`kind`, `id`, latency, status).                               |
| **Retry / Idempotency** | T-HTTP, T-SQL, T-NATS MUST implement idempotent retry where applicable.                              |
| **Schema Validation**   | Pydantic validation on inputs & outputs; runtime enforces contract.                                  |
| **Security**            | Secrets via environment-based Vault adapter; no raw secrets in config.                               |
| **Packaging**           | All starter components in `ice_builtin` Python package; auto-discovered via entry-points on install. |
| **Docs**                | Each capability auto-generates a Markdown page (`docs/`) + sample `.ai` blueprint snippet.           |

---

## 6  API & Entry-Point Conventions

| Aspect                          | Value                                                                                                                                                 |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Entry-point group for tools** | `"ice.tools"`                                                                                                                                         |
| **Entry-point group for nodes** | `"ice.nodes"`                                                                                                                                         |
| **Versioning**                  | SemVer; breaking changes bump major.                                                                                                                  |
| **Card Generation**             | Each new capability automatically registered in the **Capability Catalog** with default card fields populated from `setup.cfg` metadata or `__doc__`. |

---
