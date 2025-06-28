# Frosty Demo – Taylor's Personal Brand Growth System  
*Demo walkthrough for iceOS v0.x*

---

## 1  Why This Demo?
Taylor – a 26-year-old marketing freelancer – wants to 5× her content output without losing her authentic voice.  The demo shows how **iceOS** orchestrates LLM nodes and deterministic tools to automate Taylor's content workflow today (manual chain) and paves the way for the future Frosty platform agent.

> **Outcome Targets (90 days)**  
> • Content output → *3 / wk → 5-7 / day*  
> • Engagement rate → *4.2 % → 8.5 %*  
> • Leads → *2-3 / wk → 10-15 / wk*

---

## 2  Architecture at a Glance
```mermaid
graph TD
  subgraph Knowledge
    KB[Knowledge Base]
  end
  subgraph Content_Engine
    AIDEA[IdeaGenerator (ai)] -->|voice| APPLIER[VoiceApplier (tool)]
    APPLIER --> INJECT[TestimonialInjector (tool)]
    INJECT --> LEN{Length Check (condition)}
    LEN -- pass --> FORMAT[FormatOptimizer (tool)]
    LEN -- fail --> REWRITE[Rewriter (ai)]
    FORMAT --> SPLIT[PlatformSplitter (tool)]
  end
  subgraph Channels
    SPLIT --> TW[TwitterFormatter (tool)] --> POST_TW[TwitterPoster (tool)]
    SPLIT --> LI[LinkedInFormatter (tool)] --> POST_LI[LinkedInPoster (tool)]
  end
  POST_TW & POST_LI --> TRACKER[PerformanceTracker (tool)] --> OPT[OptimizationAgent (ai)] --> KB
```
Each rectangle is a **Node** executed by the async `ScriptChain` engine:
- `(ai)` → `AiNode` powered by an LLM provider.  
- `(tool)` → `ToolNode` with deterministic side-effects.  
- `(condition)` → `ConditionNode` for branching.

---

## 3  Knowledge Base Layout
```
/knowledge_base
├── voice_rules.json           # stylistic replacements
├── testimonials.csv           # "quote","topic"
├── top_content/*.json         # prior high-performers – vector-indexed
└── audience.parquet           # demographic & pain-point data
```
Persist it anywhere (local path or S3) – the tools consume absolute paths.

---

## 4  Node Configuration Snippets
Below are ready-to-run Pydantic models (Python dict / JSON) that follow the public SDK.  IDs are UUID-v4 strings shortened for readability.

### 4.1 IdeaGenerator (AiNode)
```json
{
  "id": "node-idea-1",
  "type": "ai",
  "name": "Idea Generator",
  "dependencies": [],
  "model": "gpt-4o-mini",
  "prompt": "SYSTEM:\nYou are an AI copywriter for Taylor (26-year-old marketing freelancer).\nMaintain first-person, energetic voice and end every idea with an actionable hook in <=15 words.\nReturn a JSON list called ideas containing exactly 5 strings.\n---\nUSER_INPUT: {{topic}}\n",
  "llm_config": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.8,
    "max_tokens": 300
  },
  "metadata": {
    "version": "1.0.0"
  }
}
```

### 4.2 VoiceApplier (ToolNode)
```json
{
  "id": "node-voice-1",
  "type": "tool",
  "tool_name": "VoiceApplier",
  "dependencies": ["node-idea-1"],
  "tool_args": {
    "rules_path": "./knowledge_base/voice_rules.json"
  },
  "metadata": {
    "version": "1.0.0"
  }
}
```

### 4.3 Length Check (ConditionNode)
```json
{
  "id": "node-len-1",
  "type": "condition",
  "dependencies": ["node-testimonial-1"],
  "expression": "len(context['text']) <= 280",
  "true_branch": ["node-format-1"],
  "false_branch": ["node-rewrite-1"],
  "metadata": {
    "version": "1.0.0"
  }
}
```
> Tip: any JMESPath-style expression is fine – the orchestrator only evaluates the boolean.

Add the remaining formatter and poster nodes analogously.

---

## 5  Running the Demo
### 5.1 Prerequisites
1. `git clone` this repo and `cd iceOSv1-A-`
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -e .[dev]`
4. Export at least one LLM key:  
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
5. Place the `knowledge_base/` folder at project root (or update tool args).

### 5.2 Execute via `ScriptChain`
```python
import asyncio, json
from ice_orchestrator import ScriptChain
from pathlib import Path

nodes = json.loads(Path("demo_nodes.json").read_text())

async def main():
    chain = ScriptChain(nodes=nodes, name="taylor_demo")
    result = await chain.execute()
    print(result.model_dump())

asyncio.run(main())
```
### 5.3 Execute via REST API
```bash
uvicorn app.main:app --reload &  # local dev server

curl -X POST http://localhost:8000/api/v1/workflow \
  -H "Content-Type: application/json" \
  -d @demo_request.json | jq
```
The JSON payload mirrors the `WorkflowRequest` model (list of NodeConfigs + optional initial context).

---

## 6  Observing the Run
`ScriptChain` logs each level in parallel.  Check:
- `logs/` folder or stdout for timing & retries.  
- Context cache via `GET /api/v1/nodes/{node_id}/context`.

```txt
✅  node-idea-1  0.9s
✅  node-voice-1  0.1s  (cached)
❌  node-rewrite-1  retry 1/2 …
```

---

## 7  Extending Towards "Frosty"
The future **Frosty Agent** will wrap this chain behind a conversational interface, but every component above already complies with iceOS rules:
1. **Type-Safe** – all configs are `NodeConfig` sub-classes.  
2. **Side-Effects in Tools** – posters & DB writes are `ToolNode`s.  
3. **Async** – long I/O (HTTP, DB) is `await`-ed inside tool `execute()` methods.  
4. **Event Naming** – emitted events follow `demoAgent.eventVerb` (e.g. `demoAgent.postScheduled`).

---

## 8  Next Steps for Contributors
1. `ice sdk create-node VoiceApplier` – scaffold with Pydantic schema & unit test.  
2. Write unit tests under `tests/tools/test_voice_applier.py` and run `make test`.  
3. Update docs here and open a PR – CI will enforce Ruff, MyPy & import-linter contracts.

---

Made with ☃️ & async love. 