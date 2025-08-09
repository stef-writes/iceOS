Runtime verification: LLM nodes, Tools, Agents (offline, deterministic)
===============================================================

This document explains the end-to-end verification example that proves the core
runtime works without any external dependencies. It covers:

- Stateless LLM chain (LLM1 → LLM2) with Jinja templating and dependency context
- LLM → Tool DAG with Jinja-rendered tool arguments and signature filtering
- Agent → Tool via AgentRuntime (plan→act loop)
- API-level tests that exercise the real HTTP execution endpoints

All examples run fully in-process and offline by registering deterministic
"factories" (local stubs) into the global registry.


Files and where things happen
-----------------------------

- scripts/verify_runtime.py
  - Registers local factories for LLM (gpt-4o) and writer_tool
  - Lifts token ceiling guard for the run
  - Executes LLM-only, LLM → Tool, LLM1 → LLM2, and Agent → Tool
  - Prints NodeExecutionResult payloads

- tests/integration/ice_api/test_api_end_to_end.py
  - Calls the real API (/api/v1/blueprints, /api/v1/executions) via ASGI
  - Registers the same factories in-process
  - Asserts rendered prompts and tool outputs on completion

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

- Jinja-only with StrictUndefined, no Python str.format
- Context includes:
  - top-level inputs at root and under inputs.*
  - each dependency’s output under its node id (e.g., {{ llm1.response }})
- The exact provider prompt is echoed as output.prompt.


Factories (LLM and Tool)
------------------------

- Register factories via registry:
  - register_llm_factory("gpt-4o", "module:function")
  - register_tool_factory("writer_tool", "module:function")
- The orchestrator resolves tools via the public factory API.


Semi-realistic prompts (stateless chain)
---------------------------------------

- LLM1: Generate a philosophical proposition about consciousness in one sentence.
- LLM2: Analyze the following proposition for coherence, originality, and rigor:\n{{ llm1.response }}\nProvide 3 bullet points.


Agent verification
------------------

- Minimal agent returns a decide() action selecting writer_tool and sets done=True
- AgentRuntime enforces allowed_tools, executes tool, and returns result
- Agent is stateful during the single run (plan→act); long-term memory is available but not used here


Token guard
-----------

- Optional runtime_config.max_tokens guard can abort runs
- Verification sets it to None to focus on behavior


Expected outputs
----------------

- LLM-only: rendered prompt (no braces) and deterministic response
- LLM → Tool: tool receives rendered value from LLM1 and returns uppercase
- LLM1 → LLM2: LLM2 prompt includes LLM1 response; analysis returned
- Agent → Tool: includes last_tool and tool result


How to run
----------

Runtime verifier (offline):

```
python scripts/verify_runtime.py
```

API E2E tests (offline):

```
pytest -q tests/integration/ice_api/test_api_end_to_end.py
```

Both paths register local factories at runtime and do not require network keys.