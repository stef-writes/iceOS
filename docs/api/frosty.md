# Frosty AI Service

## Overview
AI copilot for chain construction. Uses:
- Training data from `examples/scenarios/`
- Validation service (`ChainValidator`)
- Context type system (`ContextTypeManager`)

```python
from ice_sdk.services import FrostyAIService

async def create_chain(prompt: str) -> Blueprint:
    frosty = FrostyAIService()
    return await frosty.generate_chain_interactive(prompt)
```

## Interactive Workflow
```mermaid
sequenceDiagram
    User->>Frosty: "Check Berlin weather"
    Frosty->>Validator: Validate draft chain
    Validator-->>Frosty: Missing OpenWeather API key
    Frosty->>User: Ask for API key
    User->>Frosty: Provide key
    Frosty->>Orchestrator: Execute validated chain
    Orchestrator-->>User: Weather report
```

## Methods
### `generate_chain(prompt: str) -> ChainSpec`
- Auto-generates chain without user input
- Throws `ValidationError` if unresolved issues

### `generate_chain_interactive(prompt: str) -> ChainSpec`
- Interactive version that asks for missing inputs
- Implements "socratic" questioning flow 