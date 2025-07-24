# ice_core – Domain Layer

## Overview
`ice_core` contains **pure, side-effect-free** business objects for IceOS.  
It is the _lowest_ layer in the stack and therefore must remain completely
decoupled from IO, frameworks, and higher-level packages.

Typical contents:
* `models/` – typed Pydantic & Enum models shared across layers
* `exceptions.py` – domain-specific, typed error hierarchy
* `utils/` – functional helpers that are safe to import anywhere

## Quick-start
```python
from ice_core.models.llm import LLMConfig
from ice_core.models.enums import ModelProvider
from ice_core.exceptions import CoreError, ErrorCode

# Rich, unified LLMConfig with all parameters
cfg = LLMConfig(
    provider=ModelProvider.OPENAI,  # Uses enum, not string
    model="gpt-4",
    temperature=0.7,
    max_tokens=4096,
    api_key="sk-...",  # Usually from env
    timeout=30
)
# Note: LLMConfig doesn't have is_valid() method - Pydantic validates on creation
```

## Contract & Rules
* **No side-effects** – pure functions / dataclasses only.
* **No outward imports** – MUST NOT import `ice_sdk`, `ice_orchestrator`, `ice_api`,
  or any framework code.  
* Raise only the typed exceptions defined in this layer.

## Development
```bash
# run full suite (unit, type, lint)
make test
```
`mypy --strict` must pass before PRs merge. Test coverage ≥90 %.

## License
MIT – see top-level `LICENSE`. 