# ice_tools – First-party Tools

This package ships example/demo tools that register factories with the unified
registry. Tools under `generated/` are importable and use the pattern:

```python
from ice_core.unified_registry import register_tool_factory
register_tool_factory("writer_tool", "ice_tools.generated.writer_tool:create_writer_tool")
```

The orchestrator loads these via an explicit plugin loader during
`initialize_orchestrator()` (no import side-effects required by callers).

Usage:

```python
import ice_orchestrator
ice_orchestrator.initialize_orchestrator()  # loads first-party tools

from ice_core.unified_registry import registry
assert registry.has_tool("writer_tool")
```

