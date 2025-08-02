# Frosty – Natural-Language Workflow Generator

Frosty converts conversational prompts into executable iceOS blueprints.
It is split into two sub-packages:

| Package            | Responsibility                               |
|--------------------|----------------------------------------------|
| `frosty.core`      | Planning, validation, LLM provider registry  |
| `frosty.codegen`   | Writers that emit Blueprint JSON or Python   |

The top-level `frosty` package only contains the **CLI** (`frosty.cli`) so end-users
have a single entry-point while keeping clean import boundaries.

```
Prompt ─► frosty.cli (Typer) ─► frosty.core.agent ─► LLM provider
                                   │
                                   ▼
                             PartialBlueprint
                                   ▼
                         frosty.codegen.json_writer
                                   ▼ HTTP
                         ice_api  →  ice_orchestrator
```

## Installation
```
poetry install -E frost          # optional extras once providers need deps
```

## Generate & Run (dev stack)
```bash
make dev-up                                 # start Redis + API
poetry run frost generate "say hello to Ada" --provider o3
```
The stub `o3` provider recognises the pattern and returns a one-node spec which
is pushed and executed automatically, streaming:
```json
{
  "status": "completed",
  "result": {"greeting": "Hello, Ada!"}
}
```

## Adding a Provider
Create `frosty/core/providers/<name>.py`:
```python
from frosty.core.providers.base import LLMProvider

class MyProvider:
    name = "superllm"
    async def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        return "{}"  # call real API in production

PROVIDER: LLMProvider = MyProvider()
```
Import side-effect registers it; verify with:
```
poetry run frost providers list
```

## Import Rules
* `frosty` (CLI) → may import only `frosty.core`, `ice_core`, `ice_builder.public`.
* `frosty.core` and `frosty.codegen` → **must not** import `frosty` (CLI) to avoid cycles.
