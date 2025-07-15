# Frosty Agent Framework Overview

Frosty provides **meta-agents** that design, optimise and test ScriptChains.

Modules:

* `frosty.agents.flow_design` – Chat-GPT-like assistant to draft chains.
* `frosty.agents.prompt_engineer` – Optimises prompts via looped evaluation.
* `frosty.agents.chain_tester` – Property-based tests over chains.

All frosty code is self-contained; it only depends on `ice_sdk` public APIs. 