# Contribution Guidelines

## Code Quality Gates
- All new code must pass:
  ```bash
  make test && mypy --strict src/ && pyright
  ```
- 90% test coverage on new/changed code (CI enforces this)
- Pydantic models for all public APIs

## Deprecation Process
1. Annotate with `@deprecated` decorator
2. Log structured warning with replacement path
3. Maintain for 2 minor versions before removal 