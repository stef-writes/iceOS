<!-- AUTO-GENERATED: DO NOT EDIT DIRECTLY -->
        # iceOS Architecture Overview

        ## High-level flow

        ```
User ─▶ Frosty/Builder (ice_builder)
            ↓ Blueprint
MCP API     (ice_api)
            ↓
Orchestrator (ice_orchestrator)
            ↓
Client / CLI (ice_client · ice_cli)
```

        ## Layer responsibilities

        | Layer | Responsibilities | May import from | Py modules |
|------|------------------|-----------------|-----------|
| **ice_api** | HTTP/WS gateway, validation, persistence | orchestrator, core | 12 |
| **ice_orchestrator** | Runtime engine – executes workflows | core | 67 |
| **ice_builder** | Author-time DSLs & toolkits | core | 37 |
| **ice_core** | Pure models, protocols, registry | — | 78 |

        ## Node types

        | Node Type | Config class | Purpose |
|-----------|--------------|---------|
