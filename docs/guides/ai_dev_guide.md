# Guide: AI Development Discipline for iceOS

**Purpose:**  
To ensure AI-generated code contributes positively to iceOS development without introducing drag, architectural bloat, or wasted effort. This guide outlines best practices, known pitfalls, and a tiered enforcement model to help you apply AI codewriting responsibly.

---

## 🔁 Philosophy

> **“Lock down the stable layers. Loosen up the moving parts.”**

AI tooling can create **high-fidelity noise**: syntactically correct, beautifully linted, but contextually unnecessary abstractions. Use AI to **amplify clarity**, not to simulate polish.

---

## ⚠️ Common AI Code Pitfalls (and When to Avoid Them)

| Practice                        | When It Slows You Down                                   | When It's Worth It                                        | Mitigation Strategy                          |
|--------------------------------|-----------------------------------------------------------|-----------------------------------------------------------|----------------------------------------------|
| **Overzealous Type Hinting**   | Fighting mypy stubs or generics during early R&D         | In SDKs or public APIs where correctness is critical      | Use `mypy.ini` with relaxed rules per module |
| **Premature Mutation Testing** | Running `mutmut` on unstable files or fast-changing logic| On core orchestrator functions and tool interfaces        | Enforce only on `diff`, not entire repo      |
| **Docstring Obsession**        | Writing full docblocks for throwaway prototypes           | When exposing a public API or stable orchestration method | Use `@public` decorator to mark doc targets  |
| **Linting on Save**            | Distracts during spike/prototype cycles                  | On `main` or before releases                              | Lint only on merge or main branch pushes     |
| **Early Observability Setup**  | OTEL spans in logic that keeps shifting weekly            | When DAGs and core execution paths stabilize              | Use `structlog` + `TRACE_ENABLED` flag       |
| **Abstraction Addiction**      | Premature registries, factories, inheritance hierarchies | When multiple copies emerge and reuse becomes painful     | Copy-paste first, refactor later              |
| **Over-polished CI Pipelines** | Blocking PRs on perf/coverage/security before stable      | Once product reaches release or multi-contributor scale   | Run gates manually, block only critical ones |

---

## 🔒 Apply Enforcement Based on Layer Stability

| Module or Layer                | Lock Tight Now? | Reason                                                                 |
|-------------------------------|------------------|------------------------------------------------------------------------|
| `ice_sdk.tools` + `utils`     | ✅ Yes            | Reusable primitives. Bugs propagate widely.                            |
| `ice_orchestrator.execution`  | ✅ Yes            | Core orchestration logic. Stability is essential.                      |
| `graph_config`, `agents`, `dsl`| ⚠️ Maybe         | Allow iteration. Tighten gradually as designs stabilize.               |
| `cli`, `demos`, `experiments` | 🚫 No             | Prioritize fast iteration and feedback over polish.                    |

---

## ✅ AI Usage Checklist (Per Module / Branch)

Before using AI to generate or refactor code, validate against the following questions:

1. **Is this module stable or still evolving?**
   - ✅ Stable → High standards (type hints, tests, docs)
   - ⚠️ Evolving → Use looser standards (just make it run)

2. **Does this code touch shared infrastructure or DAG logic?**
   - ✅ Yes → Test coverage and typing matter
   - 🚫 No → Use light discipline, skip lint if needed

3. **Am I copy-pasting abstractions that I haven’t needed twice yet?**
   - 🚨 Yes → You’re likely abstracting too soon

4. **Is the AI proposing a factory, decorator, or new base class?**
   - 🚧 Pause. Only introduce if it's solving *real* duplication or complexity

5. **Is this code easy to delete?**
   - ✅ Great → You’re prototyping the right way

---

## 🧪 Development Tier Policy

| Tier          | Description                                    | Standards                         |
|---------------|------------------------------------------------|-----------------------------------|
| **Stable Core** | Orchestrator, ToolService, GraphExecutor     | `mypy --strict`, tests ≥ 90%, docstrings required |
| **Utility Layer** | SDK helpers, adapters, CLI commands         | Type hints preferred, tests where possible |
| **Experimental** | DSL sketches, unlaunched agents, demos       | No tests/docstrings required, must run |
| **Public API**   | Anything exposed to user/developers          | Docstrings + examples mandatory, mutation tested |

---

## 🧠 Dev Hygiene Principles (AI Edition)

1. **Clarity > Cleverness.** Prefer readable, unabstracted code over AI-fancy structures.
2. **Copy First, Abstract Later.** Two is a coincidence. Three is a pattern. Abstract then.
3. **Let It Be Ugly If It's Temporary.** Don’t polish prototypes.
4. **Delete Aggressively.** Don’t let dead code linger. Archive in a scratch module if needed.
5. **Ask AI to Explain Its Choices.** Don’t accept registry/factory patterns without justification.

---

## 🛠 Tooling Recommendations

- `mypy.ini`: Per-module strictness
- `Makefile`: Include soft vs hard quality targets
- `TRACE_ENABLED=1`: Gate observability logic
- `@public`: Decorator for docstring-required functions
- `.github/workflows/ci.yml`: Minimal lint-type-test only

---

## ⏭ Next Steps

1. Save this as: `docs/ai_dev_guide.md`
2. Create `mypy.ini` with per-module strict settings
3. Add `@public` decorator in `ice_sdk.decorator`
4. Keep a `/scratch/` module for parked code experiments

---

