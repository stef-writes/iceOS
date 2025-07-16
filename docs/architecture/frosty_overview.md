# Frosty Agent Framework Overview

Frosty provides **meta-agents** that design, optimise and test ScriptChains.

Modules:

* `frosty.agents.flow_design` – Chat-GPT-like assistant to draft chains.
* `frosty.agents.prompt_engineer` – Optimises prompts via looped evaluation.
* `frosty.agents.chain_tester` – Property-based tests over chains.

All frosty code is self-contained; it only depends on `ice_sdk` public APIs. 

## Layering & Relationship with iceOS

Frosty is **not** a replacement for iceOS – it is a *meta-layer* that sits **on top** of the core runtime:

```
User / Chat UI ⇄ Frosty (meta-agents, CLI UX)
                    ⇓
                iceOS Runtime (nodes, tools, ScriptChains, vector search)  
```

* Frosty interprets high-level goals, plans new `ScriptChain`s, scaffolds tools and delegates **execution** to iceOS.
* All heavy lifting – budget enforcement, KnowledgeService / EnterpriseKBNode, LLM calls – remains inside the iceOS layers.
* Frosty communicates through **public** SDK APIs only, respecting the layer boundary rule: _never import from `app.*` inside `ice_sdk.*`._

> As iceOS matures, Frosty will gradually drop its in-file stubs (e.g. `MemoryStore`) and adopt the production services directly. 