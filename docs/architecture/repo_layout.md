# Repository Layout

```
src/           # importable code
  frosty/
  ice_core/
  ice_orchestrator/
  ice_sdk/
  ice_cli/
services/      # deployables (FastAPI, worker)
docs/          # MkDocs sources
.tests/        # unit & integration tests
```

Decision 2024-06-05 (ADR-0001): keep all code importable by Python under
`src/` to simplify tooling; only runtime entry-points live in `services/`. 