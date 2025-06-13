# iceOS v1
[![CI](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml/badge.svg)](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml)

The open-source **Intelligent Composable Environment** for building agentic workflows on top of your data, services, and events.

## 🚀 Quick Start

```bash
# Install
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run hello world
python scripts/test_agent_flow.py
```

See [Quick Guide](docs/QUICK_GUIDE.md) for more examples.

## 🎯 What is iceOS?

iceOS provides a flexible framework for building AI-powered applications through:

- **Pluggable SDK** (`ice_sdk`) - Core abstractions and runtime
- **Reference App** (`app`) - Ready-to-use implementations
- **Modern Architecture** - Async-first, type-safe, event-driven

## 🏗️ Architecture

| Layer | Purpose | Key Components |
|-------|---------|----------------|
| **SDK** (`ice_sdk/`) | Core abstractions | `BaseNode`, `BaseTool`, runtime helpers |
| **Agents** (`app/agents/`) | Workflow orchestration | Agent implementations, Chain coordination |
| **Chains** (`app/chains/`) | Multi-step workflows | Scripted/declarative Chains |
| **Nodes** (`app/nodes/`) | Domain logic | Specialized `BaseNode` implementations |
| **Tools** (`app/tools/`) | Side effects | DB, HTTP, file I/O, LLM providers |
| **Events** (`app/event_sources/`) | Triggers | Webhooks, schedulers, external events |
| **Services** (`app/services/`) | Pure utilities | Vector indexes, caching, etc. |
| **Schemas** (`schemas/`) | Data models | Shared Pydantic models |

## 🔧 Key Features

- **Type Safety**: Comprehensive type hints and Pydantic models
- **Async First**: Non-blocking I/O and efficient resource usage
- **Event-Driven**: Standardized event system (`source.eventVerb`)
- **Clean Architecture**: Clear layer boundaries and dependency rules
- **Extensible**: Easy to add new Tools, Nodes, and Agents

## 📚 Documentation

- [Quick Guide](docs/QUICK_GUIDE.md) - Get started fast
- [Codebase Overview](docs/codebase_overview.md) - Architecture details
- [API Reference](docs/api/) - Detailed API docs
- [Examples](examples/) - Sample implementations

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code standards
- PR process
- Project structure

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## Deprecation notice for `ice_tools`

`ice_tools` currently exists as a *shim* that re-exports classes from
`ice_sdk.tools` and `ice_sdk.providers`.

* The shim raises `DeprecationWarning` at import time.
* It will be **removed in v0.4** of the SDK.  Down-stream code should migrate
  to `ice_sdk.tools` and `ice_sdk.providers` immediately.
