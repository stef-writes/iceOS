# 🧊 iceOS Engineering Quality & Architecture Standards

> **Purpose** — This living guide codifies the structural, architectural, and quality rules that keep iceOS maintainable, modular, and scalable as the system and team grow. Treat it as the single source of truth for every code review, ADR, and roadmap discussion.

---

## 1. Foundational Principles

1. **Build for a Team of 10** Assume multiple contributors will rely on clear patterns next quarter.
2. **Intentional Complexity** Sophisticated techniques are welcome—*if* they are justified with an ADR and surrounded by tests.
3. **Fail Fast, Fix Fast** Strong static checks (type‑safety, linters) and a green CI keep master always releasable.

---

## 2. Structural & Architectural Standards

### 2.1 Guiding Principles

| # | Principle                         | Key Practices                                                                      | Benefit                             |
| - | --------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------- |
| 1 | **Single Responsibility (SRP)**   | One reason to change → one module/class/function                                   | Low coupling, easy tests            |
| 2 | **Separation of Concerns (SoC)**  | Split IO, orchestration, domain logic; stable `services/` API                      | Clear layering                      |
| 3 | **Composition > Inheritance**     | Inject explicit deps, avoid deep trees                                             | Swap implementations, simpler mocks |
| 4 | **Package‑Oriented Architecture** | Any component with >2 responsibilities → its own package                           | Avoids mega‑files                   |
| 5 | **Code‑Volume Guardrails**        | File ≤ 400 LOC, Class ≤ 75, Fn ≤ 25                                                | Forces decomposition                |
| 6 | **Explicit Collaborators**        | All deps via constructor/factory; name them                                        | Transparent data flow               |
| 7 | **Naming & Directories**          | `CamelCase` classes, `snake_case` funcs; `Tool` suffix; DAGs end `*.workflow.yaml` | Discoverability                     |
| 8 | **Logical Layer Boundaries**      | `ice_sdk → orchestrator → app`; never import upward                                | Plug‑ability                        |
| 9 | **Complexity Needs ADR**          | Big files/classes require justification                                            | Intentional architecture            |

### 2.2 Directory Blueprint

```text
ice_sdk/          # Pure utils & models
ice_orchestrator/ # Runtime & execution graph
services/         # Cross‑layer interfaces
app/              # Entrypoints (CLI, HTTP, workers)
experiments/      # Prototypes – exempt from strict rules
```

## 3. Standard for Engineering Quality

### 3.1 Quality Pillars

| Area                        | Description                         | Status  | Goal      |
| --------------------------- | ----------------------------------- | ------- | --------- |
| **Type‑safety**             | All code passes `mypy --strict`     | \~75 %  | 100 %     |
| **Tests**                   | Unit + mutation + property tests    | \~70 %  | 95 %      |
| **Docs**                    | Google docstrings + mkdocs          | \~60 %  | 100 %     |
| **Observability**           | Structured logs, OTEL, Prom metrics | \~40 %  | 100 %     |
| **Perf / Cost**             | Benchmarks & budget gates           | \~50 %  | 90 %      |
| **CI/CD**                   | Lint, type, test, perf in pipeline  | Partial | Full      |
| **Security**                | Bandit, secret scan                 | Low     | 90 %      |
| **Architecture Discipline** | ADRs for cross‑layer changes        | Light   | Mandatory |

### 3.2 Cursor Rules & Enforcements

1. New code **must** pass `mypy --strict`.
2. Side‑effects live only in **Tool** implementations.
3. Event names use `source.eventVerb` (e.g. `webhook.userCreated`).
4. `ice_sdk.*` **never** imports from `app.*`.
5. Use `async`/`await`; no blocking IO in event loop.
6. Update matching tests when logic changes.
7. All public functions include Google‑style docstrings.
8. Coverage ≥ 90 % for new code.
9. Avoid `# type: ignore`; if needed, explain inline.
10. PRs introducing cross‑layer behavior **require an ADR**.

---

## 4. Roadmap to 100 % Quality

| Track             | Tasks                                                                                                 | Target   |
| ----------------- | ----------------------------------------------------------------------------------------------------- | -------- |
| **Type Safety**   | ‑ `ice_sdk.providers.*`<br>‑ `ice_orchestrator.*`                                                     | Week 1‑3 |
| **CI/CD**         | Add `mutmut`, `hypothesis`, `bandit` gates;<br>perf benchmarks via `pyperf`; consolidate Make targets | Week 4   |
| **Observability** | OTEL spans in executor;<br>Prom exporter;<br>Grafana docker compose                                   | Week 5‑6 |
| **Documentation** | ADR templates;<br>expand mkdocs runbooks                                                              | Ongoing  |

> **Checkpoint:** CI must be all‑green with *no* skipped gates before adding new features.
