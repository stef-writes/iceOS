# Contributing to iceOS 🚀

Thank you for your interest in contributing to iceOS! This guide will help you get started with development.

## Development Workflow

> TL;DR: `make lint type test`, commit, push – the tooling does the rest.

### 0. First-time Setup

```bash
# Clone & enter repo
git clone https://github.com/stef-writes/iceOSv1-A-.git && cd iceOSv1-A-

# Install core + dev dependencies
make install

# Enable pre-commit hooks
pre-commit install -c config/.pre-commit-config.yaml
```

> The hooks will auto-format/lint each commit; CI enforces the same checks.

### 1. Start a Task

```bash
git checkout -b feat/<short-slug>   # Create feature branch
git pull origin main --rebase       # Ensure you're up-to-date

# Optional sanity check
make doctor                         # Run full healthchecks locally
```

### 2. Development Guidelines

- Follow rules in `.cursorrules`:
  - Use type hints and Pydantic models
  - Prefer async/await for I/O
  - No cross-layer imports
  - External side-effects only in Tools
  - Event names follow `source.eventVerb`

- Testing Requirements:
  - Add/update tests under `tests/`
  - Maintain test coverage
  - Include async tests where needed

- Documentation:
  - Write/update docstrings for public APIs
  - After adding Tools/Nodes/Agents/Chains:
    ```bash
    make refresh-docs   # Regenerates capability catalog & overview
    ```

### 3. Local Development

```bash
make lint     # ruff + isort
make type     # mypy
make test     # pytest
```

All checks must pass before proceeding.

### 4. Committing Changes

```bash
git add -p          # Stage selectively
git commit -m "feat: brief description"
```

The pre-commit stack runs automatically:
- ruff → black → isort → pyupgrade → mypy → pydocstyle

### 5. Pull Request Process

```bash
git push -u origin feat/<slug>
```

GitHub Actions will run:
1. `make refresh-docs`
2. `make lint`
3. `make type`
4. `make test`

All checks must pass before merging.

### 6. After Merging

```bash
git checkout main && git pull
git branch -d feat/<slug>
```

## Project Structure

### Tracked in Git
- Generated docs (`docs/codebase_overview.md`, `docs/capability_catalog.json`)
- Source code and tests
- Configuration files
- Documentation

### Ignored Files
- Virtual environments (`.venv/`, `venv/`, `.env/`)
- Build artifacts (`build/`, `dist/`, `*.egg-info/`)
- Test caches (`.pytest_cache/`, `.coverage`, `htmlcov/`)
- Tool caches (`.mypy_cache/`, `.ruff_cache/`)
- IDE files (`.vscode/`, `.idea/`)

## Need Help?

- Check the [Architecture Decision Records](ADR/) for design decisions
- Review the [codebase overview](docs/codebase_overview.md)
- Open an issue for questions or bugs

Happy contributing! ✨ 