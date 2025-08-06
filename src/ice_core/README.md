# ice_core – Foundation Layer of iceOS

`ice_core` contains the *pure*, dependency-light primitives that every other
package builds upon.  Nothing here performs network I/O or touches disk outside
of tests; this keeps cold-start time low and makes `ice_core` safe to import
from any environment (CLI, Lambda, notebook).

---

## Responsibilities

| Area | Modules / Objects | Notes |
|------|-------------------|-------|
| **Domain models** | `models/` (LLMConfig, NodeSpec, RetryPolicy …) | All Pydantic, `mypy --strict` clean |
| **Base abstractions** | `base_tool.ToolBase`, `base_node.BaseNode` | Async `execute()` + internal `_execute_impl()` |
| **Registry** | `unified_registry.registry` | Maps `(NodeType, name)` → singleton instance |
| **Validation** | `validation/*.py` | JSON-Schema generation + runtime checks |
| **LLM integration** | `llm/service.py` + provider handlers | Uniform API over OpenAI / Anthropic / DeepSeek |
| **Metrics & cost** | `metrics.py`, `costs.py` | Deterministic cost estimator used by orchestrator |
| **Exceptions** | `exceptions.py` | Typed, narrow hierarchy – avoid bare `Exception` |

## Import rules (enforced by tests)

```
ice_core  ← may import stdlib & third-party libs

# MUST NOT import from higher layers
✗ ice_builder
✗ ice_orchestrator
✗ ice_tools
```

Unit test `tests/integration/ice_core/test_architectural_boundaries.py` fails if
a forbidden import is detected.

## Creating a new Tool (Factory Pattern)

```python
from ice_core.base_tool import ToolBase
from ice_core.unified_registry import register_tool_factory

class EchoTool(ToolBase):
    """Return whatever arguments are passed in."""

    name: str = "echo"

    async def _execute_impl(self, **kwargs):
        return kwargs

# Factory function for creating fresh instances
def create_echo_tool(**kwargs):
    return EchoTool(**kwargs)

# Register factory for fresh instances on each execution
register_tool_factory("echo", "my_module:create_echo_tool")
```

## Running tests & linters (package-only)

```bash
pytest tests/unit/ice_core  -q
mypy --strict src/ice_core
ruff check src/ice_core
```

All new code must ship with ≥ 90 % coverage on changed lines and **zero**
`# type: ignore` comments.
