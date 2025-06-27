# Bitcoin Analysis & Content-Orchestration Demo

_Revision 2025-XX-XX_

This guide replaces the legacy **`slack_btc_alert.json`** and
`demo_content_repurposer_run.py` examples with a richer, type-safe ScriptChain
that demonstrates multi-step reasoning, dynamic tool usage and branching
content pipelines—using **only** OpenAI (GPT-4 / GPT-4o / o3) and **DeepSeek-R1**
models.

---

## 1 Why this demo?

* Parse fuzzy user questions about Bitcoin and decide—at runtime—what external
data is required.
* Showcase cooperative "Socratic" reasoning across three or more LLM nodes.
* Illustrate conditional tool invocation (price & news APIs) driven by LLM
  output.
* Prove that branching pipelines (3 tweets + blog _vs._ single tweet) are easy
  to express with a `ConditionNodeConfig`.
* Provide a reusable blueprint for future multi-asset "content repurposer"
  workflows.

---

## 2 Objectives

| # | Goal |
|---|-----------------------------------------------|
| 1 | Parse ambiguous user questions about Bitcoin. |
| 2 | Decide which data (price, news, technical) is needed. |
| 3 | Fetch live BTC price (and optionally news). |
| 4 | Synthesise insights via at least **3** LLM nodes. |
| 5 | Branch: generate **3 tweets + blog** _or_ a single tweet depending on volatility. |

---

## 3 Success metrics

| Metric | Target | Why it matters |
|------------------------------|-----------|------------------------------|
| End-to-end latency | < 8 s | Keeps UX snappy on free tier |
| Token budget | < 2 000 | Runs on low-cost quota |
| External API calls | ≤ 2 per run | Demonstrates conditional efficiency |
| Content accuracy | Manual spot-check passes | Ensures price references are correct |
| Branch coverage | High + low volatility paths in CI | Guarantees both pipelines work |

---

## 4 Requirements

### 4.1 LLM models

```
gpt-4o           # "GPT-4.0" real-time
gpt-4o-mini      # "o3" cost-optimised
gpt-4-turbo      # "GPT-4.1"
deepseek-r1      # DeepSeek Chat v1
```

### 4.2 Environment vars

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Access GPT-4 / o3 |
| `DEEPSEEK_API_KEY` | Access DeepSeek-R1 |
| `CMC_API_KEY`* | Fetch real BTC price |

\*The demo falls back to a mock price when `CMC_API_KEY` is unset.

### 4.3 New Tools

* **`coinmarketcap_tool.py`** – fetches BTC price & 24 h change
* **`news_api_tool.py`** – returns recent BTC headlines (optional)

Both live in `src/tools/` and follow repo rule #1 (Pydantic schema).

---

## 5 High-level flow

```mermaid
graph TD
  A[User Input<br/>"What's up with BTC?"] --> B[LLM 1<br/>Parse Input]
  B --> C[LLM 2<br/>Contextualise Needs]
  C -->|needs_price| D[Tool 1<br/>CoinMarketCap]
  C --> E[Tool 2<br/>News API]
  D & E --> F[LLM 3<br/>Synthesis]
  F --> G{Condition<br/>High Volatility?}
  G -->|Yes| H[LLM 4<br/>3 Tweets + Blog]
  G -->|No | I[LLM 4b<br/>Single Tweet]
```

---

## 6 Implementation steps

### 6.1 Scaffold tools

```bash
# From repo root
ice tool new CoinMarketCap
ice tool new NewsAPI
```

### 6.2 Tool example (CoinMarketCap)

```python
# src/tools/coinmarketcap_tool.py
from ice_sdk.tools.base import function_tool, ToolContext
from pydantic import BaseModel

class CMCRequest(BaseModel):
    currency: str = "USD"

@function_tool(name="coinmarketcap", args_schema=CMCRequest)
async def get_btc_price(ctx: ToolContext, currency: str = "USD") -> dict:
    """Return {"price": float, "change_24h": float}."""
    # ↯ Replace with real API call if CMC_API_KEY exists
    return {"price": 66123.45, "change_24h": -1.2}
```

Analogous implementation for `news_api_tool.py`.

### 6.3 ScriptChain specification

Save as **`examples/btc_analysis.json`**:

```jsonc
[
  {
    "id": "parse_input",
    "type": "ai",
    "model": "gpt-4o",
    "prompt": "From '{{user_input}}' output JSON {needs_price:boolean, topics:string[], urgency:int}"
  },
  {
    "id": "contextualise",
    "type": "ai",
    "model": "deepseek-r1",
    "dependencies": ["parse_input"],
    "prompt": "Given {{parse_input.output}}, list required_data_types[] (price, news, technical)"
  },
  {
    "id": "get_price",
    "type": "tool",
    "tool": "coinmarketcap",
    "dependencies": ["contextualise"],
    "condition": "{{parse_input.output.needs_price}}"
  },
  {
    "id": "get_news",
    "type": "tool",
    "tool": "news_api",
    "args": {"query": "Bitcoin"},
    "condition": "{{'news' in contextualise.output.required_data_types}}"
  },
  {
    "id": "synthesis",
    "type": "ai",
    "model": "gpt-4o-mini",
    "dependencies": ["get_price", "get_news"],
    "prompt": "Summarise: price={{get_price.output.price}}, change={{get_price.output.change_24h}}, news={{get_news.output}}"
  },
  {
    "id": "route",
    "type": "condition",
    "expression": "{{abs(get_price.output.change_24h) > 5}}",
    "true_branch": ["generate_rich_content"],
    "false_branch": ["generate_simple_tweet"]
  },
  {
    "id": "generate_rich_content",
    "type": "ai",
    "model": "gpt-4-turbo",
    "prompt": "Write 3 engaging tweets *and* a 300-word blog using {{synthesis.output}}"
  },
  {
    "id": "generate_simple_tweet",
    "type": "ai",
    "model": "deepseek-r1",
    "prompt": "Write one calm tweet about BTC based on {{synthesis.output}}"
  }
]
```

### 6.4 Directory layout

```
docs/
  demos/btc_analysis_demo.md   ← this guide
examples/
  btc_analysis.json            ← ScriptChain spec
src/tools/
  coinmarketcap_tool.py
  news_api_tool.py
```

---

## 7 Running the demo

```bash
ice run examples/btc_analysis.json \
     --input "Heard Bitcoin is tanking—should I worry?" \
     --model gpt-4o
```

Expected (abridged) output:

```json
{
  "success": true,
  "output": {
    "generate_rich_content": {
      "tweets": ["⚠️ BTC just slid 5.4 %…", "…", "…"],
      "blog": "## Bitcoin's Rough Morning\nToday BTC dipped below…"
    }
  },
  "token_stats": {"total_tokens": 1325}
}
```

---

## 8 Validation matrix

| Scenario | Expected path | Check |
|----------|---------------|-------|
| Query mentions only news | Skips `get_price` | ≤ 1 external call |
| Volatility ≥ 5 % | Rich-content branch | tweets == 3 & blog exists |
| Volatility < 5 % | Simple tweet branch | tweet ≤ 280 chars |
| Re-run identical input | Cache hit | 2× runtime < 3 s |

Automate via `tests/test_btc_chain.py`.

---

## 9 Extending the flow

* **Sentiment analysis**: insert `sentiment_tool` before router.
* **Localisation**: duplicate content nodes per language & branch accordingly.
* **Scheduling**: wrap chain in a cron-triggered webhook node.

---

## 10 Legacy cleanup

```bash
git rm examples/slack_btc_alert.json
git rm scripts/demo_content_repurposer_run.py
```

The new **btc_analysis** demo supersedes both, offering clearer structure,
richer reasoning and a fully type-safe, test-backed ScriptChain.

---

_End of document_ 