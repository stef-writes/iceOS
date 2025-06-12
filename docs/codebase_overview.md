# iceOS Codebase Overview

> Last updated: 2024-03-26

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
   - Type-safe data models using Pydantic
   - Context management and utilities

3. **Tool Layer** (`ice_tools/`)
   - Side-effecting operations and integrations
   - LLM provider implementations
   - Built-in tool implementations

4. **Agent Layer** (`ice_agents/`)
   - Agent orchestration and coordination
   - Chain and Node implementations
   - Agent-specific utilities

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
│   ├── ice_sdk/           # Core SDK
│   ├── ice_tools/         # Tool implementations
│   ├── ice_agents/        # Agent orchestration
│   └── ice_orchestrator/  # Workflow engine
├── tests/                 # Test suite
├── docs/                  # Documentation
├── examples/              # Example implementations
├── config/               # Configuration files
├── schemas/              # JSON schemas
└── scripts/              # Utility scripts
```

## Getting Started

1. Install dependencies: `poetry install`
2. Run tests: `make test`
3. Start development server: `make dev`
4. Check code quality: `make lint`

For detailed information about specific components, refer to their respective README files and the `CAPABILITY_CATALOG.json` for available features. 