# iceOS E-Commerce Toolkit (Scaffold)

*Status: design-phase – no runnable code yet.*

This directory will evolve into a **self-contained toolkit** implementing all
commerce-specific building blocks required for the “Kim’s Morning Workflow”
demo:

| Planned Tool | Purpose |
|--------------|---------|
| `PricingStrategyTool` | Deterministic cost → price calculation with margin & rounding rules |
| `TitleDescriptionGeneratorTool` | Generate marketplace-ready copy via LLM |
| `MarketplaceClientTool` | Async HTTP POST to create listings on external marketplaces |
| `AggregatorTool` | Summarise per-row results (success/failure, stats) |

The toolkit follows the global project rules:

1. Pure Pydantic models & type hints – **no** `# type: ignore` escape hatches.
2. External side-effects restricted to `_execute_impl` (Tool rule #2).
3. Tools auto-register via `ice_core.unified_registry.registry` on import.
4. `async`/`await` everywhere; network and file I/O never block the event loop.
5. ≥ 90 % test coverage, enforced in CI.

> **Next steps**
>
> 1. Design `PricingStrategyTool` API & unit tests
> 2. Implement logic + register instance
> 3. Iterate for remaining tools
