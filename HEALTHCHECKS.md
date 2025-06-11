# Healthchecks

> Run `python scripts/doctor.py` or `make doctor` to execute all checks. Each check exits with non-zero on failure.

| # | Check | Command | Expected Output |
|---|--------|---------|-----------------|
| 1 | Linting (ruff) | `ruff src/` | No violations. |
| 2 | Typing (mypy) | `mypy src/` | Success: "Success: no issues found". |
| 3 | Unit tests | `pytest -q` | All tests pass. |
| 4 | Security audit | `pip-audit` | No known vulnerabilities. |
| 5 | Imports sorted | `isort --check-only src/` | Passed | 
| 6 | Docstyle | `pydocstyle src/` | No errors. |
| 7 | JSON/YAML validity | `python -m scripts.check_json_yaml` | 0 invalid files. |
| 8 | CLI help | `python src/app/main.py --help` | Usage screen without error. |
| 9 | ⏱️ Performance smoke | `python scripts/doctor.py --perf` | < 2s per core suite. |
|10 | Coverage threshold | `pytest --cov=src --cov-fail-under=75` | ≥ 75% coverage. |
|11 | Gen-doc freshness | `make refresh-docs` then `git diff --exit-code` | No diff. |
|12 | Licensing headers | `python scripts/check_license.py` | All source files have header. | 