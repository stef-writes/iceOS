# Frosty – Natural-Language Interpreter

Frosty is the **Interpreter layer** of iceOS.  It turns user messages into validated blueprints that the MCP compiler and Orchestrator can execute.

## What’s in this Package
| Directory | Purpose |
|-----------|---------|
| `cognitive/` | Perception, reasoning, memory, synthesis, metacognition scaffolds |
| `dialogue/`  | Clarification / confirmation flow management |
| `blueprint/` | Intent → `PartialBlueprint` generation and MCP validation |
| `models/`    | Pydantic models for intent & cognitive state |
| `prompts/`   | Prompt templates for cognitive subsystems |

The cognitive subsystem follows a **Plan-Observe-Iterate** loop and uses **ice_orchestrator.memory.UnifiedMemory** for working, episodic, semantic, and procedural memory.

## Current Status
* Directory scaffold and detailed docstrings are in place (no runtime code yet).
* Full integration comments explain how each module will leverage iceOS components.
* Frosty is **not** wired into the API server yet – that will happen once the MVP cognitive loop is implemented.

## Next Steps
1. Implement `cognitive.orchestrator.CognitiveOrchestrator` MVP.
2. Wire Dialogue manager to FastAPI route (in `ice_api`).
3. Generate real `PartialBlueprint` objects and submit to MCP compile tier.
4. Incrementally add tool synthesis and metacognitive learning.

---
MIT License · © iceOS Contributors 