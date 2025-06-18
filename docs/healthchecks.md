# Health-check Matrix

Run `make doctor` (wrapper for `python -m scripts.doctor`) to execute the full suite.  
Each row below is also runnable standalone.

| # | Check | Command | Expected Output |
|---|--------|---------|-----------------|
| 1 | Linting (ruff) | `ruff src/` | No violations |
| 2 | Typing (pyright) | `pyright` | 0 errors |
| 3 | Unit & integration tests | `make test` | All tests pass |
| 4 | Coverage threshold | `pytest --cov=ice_sdk --cov=ice_orchestrator --cov-fail-under=54` | ≥ 54 % coverage |
| 5 | Security audit | `pip-audit` | 0 vulnerabilities |
| 6 | Import-linter rules | `python -m importlinter` | All contracts green |
| 7 | isort check | `isort --check-only src/` | Passed |
| 8 | JSON/YAML validity | `python -m scripts.check_json_yaml` | 0 invalid files |
| 9 | Schema generation drift | `python -m scripts.generate_schemas && git diff --exit-code schemas/runtime` | No diff |
|10 | Doc build freshness | `make refresh-docs && git diff --exit-code docs/` | No uncontrolled diff |
|11 | ⏱️ Perf smoke | `python -m scripts.doctor --perf` | < 2 s per suite |
|12 | License headers | `python -m scripts.check_license` | Headers present | 