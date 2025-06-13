# iceOS Codebase Overview

> Last updated: 2025-06-13
> Last updated: 2025-06-14

## Project Overview

iceOS is an Intelligent Composable Environment platform that enables building and orchestrating AI-powered applications through a modular, type-safe architecture. The platform emphasizes clean separation of concerns, async-first design, and robust type checking.

## Architecture

The codebase follows a layered architecture:

1. **Application Layer** (`app/`)
   - FastAPI web server and API endpoints
   - Business logic and workflow definitions
   - Database models and migrations

2. **Core SDK** (`ice_sdk/`)
   - Base abstractions and interfaces
   - `ice_sdk.interfaces/` – lightweight `Protocol` contracts (e.g., `ScriptChainLike`) that let SDK reference outer layers without violating boundaries
   - Type-safe data models using Pydantic
   - Context management and utilities

3. **Executor & Tool Layer** (`ice_sdk/tools/` + `ice_sdk/executors/`)
   - Deterministic tool implementations
   - Node-executor registry (mode → executor)
   - Built-in web/file search tools, etc.

4. **Agent Layer** (`ice_sdk/agents/`)
   - AgentNode runtime for LLM reasoning
   - Planner/Verifier agents (future)

5. **Orchestration Engine** (`ice_orchestrator/`)
   - Workflow execution and management
   - Event handling and callbacks
   - Metrics and monitoring
   - Configuration management

## Key Design Principles

1. **Type Safety**
   - Comprehensive type hints throughout
   - Pydantic models for data validation
   - Strict type checking with MyPy and Pyright

2. **Async-First**
   - All I/O operations are async
   - Non-blocking event loop
   - Efficient resource utilization

3. **Clean Architecture**
   - Clear layer boundaries
   - Dependency injection
   - Separation of concerns

4. **Event-Driven**
   - Event-based communication
   - Standardized event naming (`source.eventVerb`)
   - Observable system state

## Development Infrastructure

### Testing
- Comprehensive test suite in `tests/`
- Async test support with pytest-asyncio
- Coverage reporting and benchmarks

### Code Quality
- Poetry for dependency management
- Black and isort for formatting
- Ruff for linting
- Pyright (basic mode) and MyPy for static type checking — strictness will be increased incrementally
- Import-linter for dependency rules

### Documentation
- API documentation
- Example implementations
- Architecture Decision Records (ADR)

## Directory Structure

```
.
├── src/                    # Source code
│   ├── app/               # Application layer
│   ├── ice_sdk/           # Core SDK (+ tools, agents, executors)
│   └── ice_orchestrator/  # Workflow engine
├── tests/                 # Test suite
├── docs/                  # Documentation
├── examples/              # Example implementations
├── config/               # Configuration files
├── htmlcov/               # Local coverage reports (git-ignored)
├── schemas/               # JSON schemas (auto-generated)
└── scripts/              # Utility scripts
```

## Getting Started

1. Install dependencies: `poetry install`
2. Run tests: `make test`
3. Start development server: `make dev`
4. Check code quality: `