# Frosty – Compiler & Thinking Partner

## What is Frosty?
Frosty is the **compiler** and **thinking partner** for IceOS workflows. While IceOS
provides the runtime execution engine, Frosty handles the creative and analytical
work of designing, optimizing, and validating ScriptChains.

Think of it as:
- **Compiler**: Converts high-level intent → executable ScriptChains
- **Thinking Partner**: Collaborates on design, debugging, and optimization
- **Quality Assurance**: Tests, validates, and refines workflows

| Agent | Responsibility |
|-------|----------------|
| FlowDesignAgent   | Draft chains from high-level specs |
| NodeBuilderAgent  | Scaffold new nodes & tools         |
| PromptEngineerAgent | Auto-tune prompts via evaluation |
| ChainTesterAgent  | Property-based testing             |

Frosty never executes chains itself; it delegates to the IceOS runtime via
`ice_sdk` public APIs.

## Example: Compile Intent to Chain
```python
from frosty import FlowDesignAgent

# Frosty as compiler: convert intent → executable
agent = FlowDesignAgent()
chain_spec = await agent.design_chain("build a PDF summariser")
print(chain_spec.to_mermaid())

# Frosty as thinking partner: debug and optimize
from frosty import PromptEngineerAgent
optimizer = PromptEngineerAgent()
improved_chain = await optimizer.optimize_prompts(chain_spec)
```

## Repo Structure
```
frosty/
├─ agents/          # Meta-agents
├─ context.py       # Shared agent context
├─ exceptions.py
└─ …
```

## Architecture Relationship
```
User Intent → Frosty (Compiler/Thinking Partner) → ScriptChain → IceOS (Runtime)
```

Frosty focuses on the **design-time** work while IceOS handles **runtime execution**.
This separation allows Frosty to be a sophisticated thinking partner without
compromising the performance and reliability of the execution engine.

## Development
* Agents are **async** – integration tests live in `tests/agents`.
* Follow SDK layer rules (no imports from `ice_api`, `ice_cli`, …).

## License
MIT. 