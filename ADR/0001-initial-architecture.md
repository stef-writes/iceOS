# ADR-0001: Initial Architecture

Date: 2025-06-11

## Status

Accepted

## Context

We need a clear separation between the *framework* (`ice_sdk`) and the *reference application* (`app`) so that external adopters can depend on the SDK without vendor-locking into our implementation details.

## Decision

1. Keep `ice_sdk` free of application imports.
2. Expose extension points via abstract base classes (`BaseNode`, `BaseTool`).
3. Encapsulate side-effects in Tools; Nodes remain pure / deterministic.
4. All orchestrations happen in **Chains**, which can be executed by Agents or directly.

## Consequences

+ Developers can build their own Apps on top of the SDK.
+ Easier unit testing because side-effects are isolated.
+ Versioning: major bumps only when SDK contracts break.

---

See also `.cursorrules` for enforcement guidelines. 