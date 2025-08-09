Runtime verification: live providers and offline mode
=====================================================

This document explains the end-to-end verification examples that prove the core
runtime works end-to-end with real providers (OpenAI, SerpAPI) and also in a
fully deterministic, offline mode. It covers:

- Stateless LLM chain (LLM1 → LLM2) with Jinja templating and dependency context
- LLM → Tool DAG with Jinja-rendered tool arguments and signature filtering
- LLM → SearchTool → LLM (SerpAPI live + OpenAI live)
- Agent → Tool via AgentRuntime (plan→act loop) with intra-run memory
- Swarm node via a simple factory (deterministic consensus)
- API-level tests that exercise HTTP execution endpoints

Live mode uses provider keys in your environment. Offline mode registers
deterministic "factories" (local stubs) into the global registry.


Files and where things happen
-----------------------------

- scripts/verify_runtime.py
  - Live: runs LLM-only, LLM → Tool, LLM → SearchTool → LLM, LLM1 → LLM2,
    Agent → Tool (intra-run memory), and Swarm (factory)
  - Offline: can register deterministic factories if desired
  - Lifts token ceiling guard for verification runs
  - Prints `NodeExecutionResult` payloads

- tests/integration/ice_api/test_api_end_to_end.py
  - API E2E for LLM and Tool nodes via ASGI
  - Registers factories in-process; asserts rendered prompts and outputs

- tests/integration/ice_api/test_api_search_code_swarm.py
  - API E2E for SearchTool, Code node, and Swarm node

- Core runtime touched
  - Jinja templating in llm/tool executors and helpers
  - Token ceiling enforcement in workflow.py
  - Tool resolution via public factory API in ToolExecutionService


Blueprint and MCP usage
-----------------------

API expects a Blueprint made of MCP NodeSpec objects. The runtime converts
them to concrete NodeConfig via convert_node_specs.

- Common fields: id, type, dependencies
- LLM-specific: model, prompt, llm_config
- Tool-specific: tool_name, tool_args

Execution is level-ordered by dependencies.


Templating and context propagation
----------------------------------

- Jinja-only with StrictUndefined, no Python `str.format()` (lint-banned)
- Context includes:
  - top-level inputs at root and under inputs.*
  - each dependency’s output under its node id (e.g., {{ llm1.response }})
- The exact provider prompt is echoed as output.prompt.


Factories (LLM, Tool, Agent, Swarm)
-----------------------------------

- Register factories via registry (examples):
  - register_llm_factory("gpt-4o", "module:function")
  - register_tool_factory("writer_tool", "module:function")
  - register_agent_factory("writer", "module:function"); register_agent_factory("reviewer", "module:function")
  - register_swarm_factory("simple_swarm", "module:function") and/or under the node id (e.g., "swarm1")
- The orchestrator resolves via public factory APIs only.


Semi-realistic prompts (stateless chain)
----------------------------------------

- LLM1: Generate a philosophical proposition about consciousness in one sentence.
- LLM2: Analyze the following proposition for coherence, originality, and rigor:
  {{ llm1.response }}
  Provide 3 bullet points.

Search + summarize (live)
-------------------------
- LLM1: Prompt to generate a search query
- SearchTool: queries SerpAPI with that text
- LLM2: Summarize the top result injected via context (e.g., {{ search.results[0] }})

Swarm (factory)
---------------
- Registers a minimal consensus swarm factory under both a generic name and the node id
- Returns a deterministic consensus over two simple agents (writer, reviewer)


Agent verification
------------------

- Minimal agent returns a decide() action selecting writer_tool and sets done=True
- AgentRuntime enforces allowed_tools, executes tool, and returns result
- Agent is stateful during the single run (plan→act); long-term memory optional
- Intra-run memory example writes then reads within a single run


Token guard
-----------

- Optional runtime_config.max_tokens guard can abort runs
- Verification sets it to None to focus on behavior


Expected outputs (abridged)
---------------------------

- LLM-only: rendered prompt (no braces) and model + usage fields
- LLM → Tool: tool receives rendered value from LLM1 and returns uppercase
- LLM → SearchTool → LLM: search results from SerpAPI; LLM summarizes top result
- LLM1 → LLM2: LLM2 prompt includes LLM1 response; analysis text returned
- Agent → Tool: includes last_tool and tool result; intra-run memory shows write/read
- Swarm: consensus object with participating agents


How to run
----------

Runtime verifier (live):

```
make verify-live
```

Runtime verifier (offline, deterministic factories):

```
python scripts/verify_runtime.py
```

API E2E tests (offline):

```
pytest -q tests/integration/ice_api/test_api_end_to_end.py
pytest -q tests/integration/ice_api/test_api_search_code_swarm.py
```

Notes
-----
- Live runs require `OPENAI_API_KEY` and, for search, `SERPAPI_KEY`.
- Rendering uses Jinja only with StrictUndefined; Python `str.format()` is banned.