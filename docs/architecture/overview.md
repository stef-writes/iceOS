# System Overview

```mermaid
graph LR
    subgraph Client
        U[User Input]
    end
    U -->|HTTP / CLI| A(RouterAgent)

    subgraph Registry
        A_A(Node/Tool Agents):::agent
        W_A(WorkflowAgent):::agent
    end

    A -->|select| A_A & W_A
    A_A -->|execute| ToolService
    W_A -->|execute chain| SC[LevelBasedScriptChain]

    SC --> N1[LLM Node]
    SC --> N2[Tool Node]
    N1 --> ToolService

    ToolService -->|run| Tools[(Python functions / API calls)]

    style agent fill:#f0f0ff,stroke:#6c6cff,stroke-width:2px
```

Key layers:

1. **Agents** – entry points (`NodeAgentAdapter`, `WorkflowAgentAdapter`, `RouterAgent`).
2. **Chains** – deterministic orchestration (`LevelBasedScriptChain`).
3. **Nodes** – single unit of work (`AiNode`, `ToolNode`).
4. **Tools** – deterministic side-effects wrapped by `ToolService` (or `AgentTool`).
5. **Context & Memory** – `SessionState` (conversation + last outputs) and `GraphContextManager` (intermediate DAG state).

---
See [Agents & Workflows](agents.md) for a deep dive. 