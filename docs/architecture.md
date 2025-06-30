# Architecture

```mermaid
graph TD
    subgraph Web Layer
        A[FastAPI App]
        A --> B[Core Routers]
        A --> C[KB Router]
    end

    subgraph Orchestrator
        D[ScriptChain]
        D --> E[NODE Executors]
    end

    subgraph SDK
        F[Node & Agent Models]
        F --> G[ToolService]
        F --> H[GraphContextManager]
    end

    subgraph CLI
        I[Typer-based CLI]
    end

    A --> D
    D --> F
    F --> I
```

High-level layers:

| Layer | Purpose |
|-------|---------|
| **FastAPI App** | Exposes REST + real-time endpoints for orchestrator, chain-builder and knowledge-base. |
| **Orchestrator** | Executes DAGs with concurrency, caching and metrics. |
| **SDK** | Data models, executors, context and tool abstractions. |
| **CLI** | Local developer ergonomics (chain builder, tool runner, server launcher). |

Dive deeper into each component in the pages that follow. 