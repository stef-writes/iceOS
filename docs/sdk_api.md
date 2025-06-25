# iceOS SDK – Public API (v0.x)

This document lists the **stable, semver-protected symbols** that external
extensions can rely on.  Everything else is considered internal and **may
change without notice**.

## Promise

* The identifiers listed below are exported via `ice_sdk.__all__` **and re-exported unmodified under `iceos.sdk`**.
* They will not be removed or receive breaking signature changes in a **minor** version.
* Deprecations are announced at least **one minor version** in advance via
  `DeprecationWarning`. 
* Breaking removals are only allowed in a **major** version bump.

| Category | Symbol |
|----------|--------|
| Core     | `BaseNode` |
|          | `BaseTool` |
| Services | `ToolService` |
| Data     | `NodeConfig` · `NodeExecutionResult` · `NodeMetadata` |
|          | `LLMConfig` · `MessageTemplate` |
| Context  | `GraphContextManager` |

*(See `ice_sdk/__init__.py::__all__` — or `iceos.sdk.__all__` — for the single source of truth.)*

## Extending the SDK

### 1. Custom deterministic **Tool**

```python
# Either import directly from the SDK …
from ice_sdk.tools.base import function_tool

# … or use the meta-package convenience alias
from iceos.sdk.tools.base import function_tool  # identical symbol

@function_tool()
async def multiply(a: int, b: int) -> int:
    """Return `a * b`."""
```

Register the instance with a `GraphContextManager` or pass it into
`ScriptChain(tools=[multiply])`.

### 2. Custom **AI Node** with a prompt

```python
from ice_sdk.models.node_models import AiNodeConfig

my_ai_node = AiNodeConfig(
    id="summarise",
    type="ai",
    model="gpt-3.5-turbo",
    prompt="Summarise: {{text}}",
    llm_config=LLMConfig(provider="openai", model="gpt-3.5-turbo", temperature=0.2),
    input_schema={"text": "str"},
    output_schema={"summary": "str"},
)
```

Add the config to a `ScriptChain` and you're done – the orchestrator converts
it to an `AgentNode` under the hood.

## What is **not** public?

* `ice_sdk.utils.*`
* Any module or attribute not re-exported through `ice_sdk.__all__`


---

Last updated: 2025-06-14

```python
# Convenience import via meta-package
from iceos import BaseNode

# Or the canonical path
from ice_sdk.base_node import BaseNode
``` 