# ADR-0001: Initial Architecture

Date: 2025-06-11

## Status

Accepted

## Context

We need a clear separation between the *framework* (`ice_sdk`) and the *reference application* (`app`) so that external adopters can depend on the SDK without vendor-locking into our implementation details. Additionally, we need to support user-defined context management for complex workflows.

## Decision

1. Keep `ice_sdk` free of application imports.
2. Expose extension points via abstract base classes (`BaseNode`, `BaseTool`).
3. Encapsulate side-effects in Tools; Nodes remain pure / deterministic.
4. All orchestrations happen in **Chains**, which can be executed by Agents or directly.
5. Support user-defined **Context Blocks** for managing workflow state:
   - Blocks are named collections of nodes whose outputs are aggregated
   - Accessible via `context.<blockName>` in subsequent nodes
   - Managed by `GraphContextManager` in the orchestrator
   - Configurable aggregation policies (raw, last N, summarize, reduce)

## Consequences

+ Developers can build their own Apps on top of the SDK.
+ Easier unit testing because side-effects are isolated.
+ Versioning: major bumps only when SDK contracts break.
+ Context Blocks enable:
  - Fine-grained control over data flow
  - AB testing without DAG rewiring
  - Versioned and shareable workflow components
  - Enhanced governance through block-level policies

---

See also `.cursorrules` for enforcement guidelines. 