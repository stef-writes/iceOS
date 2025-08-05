# iceOS Structural Audit – 2025-08-05

This document lists **all current violations or risk areas** related to dynamic imports, hidden cross-layer dependencies, and ServiceLocator / registry abuse.

## Summary Counts

| Category | Occurrences |
|----------|-------------|
| Dynamic imports (`importlib`, `__import__`, `eval`, `exec`) | 28 |
| ServiceLocator.get outside API/Orchestrator | 8 |
| Direct unified_registry imports outside Orchestrator/Tools | 23 |
| **Total hotspots** | 59 |

*Files with zero issues are omitted from the detailed lists below.*

---

## 1. Dynamic import hotspots

```text
$(cat reports/dynamic_imports.txt)
```

---

## 2. ServiceLocator misuse (outside allowed layers)

```text
$(cat reports/service_locator_usage.txt)
```

---

## 3. Unified registry direct imports (outside Orchestrator & Tools)

```text
$(cat reports/registry_imports.txt)
```

---

> Generated automatically by `scripts/analyze_dependencies.py` and ad-hoc grep scans.

Next phase:  
1. Convert these findings into failing checks in `scripts/check_layers.py`.  
2. Refactor or suppress each hotspot commit-by-commit.
