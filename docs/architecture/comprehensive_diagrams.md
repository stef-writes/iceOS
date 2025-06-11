# iceOS – Comprehensive Architecture & Workflow Diagrams

> The following document aggregates the **deployment**, **runtime**, **data-model**, and **workflow** views of the iceOS ADK-based agent framework.  All diagrams are rendered with Mermaid so that they remain editable by developers.

---

## 1. Deployment / Infrastructure View

```mermaid
flowchart TD
    subgraph Cloud_Region[«AWS / GCP / Azure»]
        subgraph Public_Subnet
            LB[(★ Application Load Balancer)]
        end

        subgraph Private_Subnet
            API[FastAPI ‑ "ice-api"]
            Worker[ScriptChain Executor]\n(Celery / Async Pool)
            Cache[(Redis «session»)]
            DB[(PostgreSQL «metadata»)]
            VectorDB[(Weaviate «embeddings»)]
        end

        subgraph Observability
            Grafana[(Grafana)]
            Loki[(Loki Logs)]
            Tempo[(Tracing / OTel Collector)]
        end

        LB -->|HTTPS| API
        API -->|AMQP / SQS| Worker
        API --> Cache
        Worker --> Cache
        API --> DB & VectorDB
        Worker --> DB & VectorDB
        API --OTel--> Tempo
        Worker --OTel--> Tempo
        Tempo --> Grafana
        Loki --> Grafana
    end

    Developer:::actor -->|CI/CD| Cloud_Region

    classDef actor fill:#fffaf0,stroke:#333,stroke-width:1px;
```

---

## 2. Internal Runtime Component View

```mermaid
graph LR
    subgraph FastAPI_Process
        R[Router] --> EP1[/POST /v1/chat/]
        R --> EP2[/POST /v1/chains/execute/]
        R --> HealthCheck
    end

    EP1 -->|construct| ScriptChain
    EP2 -->|load config| ScriptChain

    subgraph ScriptChain[LevelBasedScriptChain]
        Scheduler -- plan --> DAG((Node DAG))
        Scheduler --> ParallelPool{{asyncio.gather}}
    end

    DAG -->|spawn| AiNode
    DAG --> ToolNode
    AiNode -->|tool-call| ToolService

    subgraph ToolService
        Registry((ToolRegistry))
        Registry --> PythonTools["🛠 Local Python" ]
        Registry --> MCPToolset
    end

    MCPToolset -->|JSON RPC| MCPServer[(Remote MCP)]

    AiNode --> LLM[OpenAI / Anthropic / Ollama]
    ToolNode & AiNode --> ContextMgr[InvocationContext]
    ContextMgr --> RedisCache[(Redis Session)]
```

---

## 3. Core Data-Model Class Diagram

```mermaid
classDiagram
    class InvocationContext {
        +str invocation_id
        +Session session
        +BaseAgent agent
        +dict state
        +ContentPartList user_content
        +save_artifact()
        +load_artifact()
    }

    class ToolContext {
        +str tool_name
        +request_credential()
        +get_auth_response()
        +search_memory()
    }
    InvocationContext <|-- ToolContext

    class BaseNodeConfig {
        +id : str
        +type : str
        +dependencies : list
        +level : int
        +provider : ModelProvider
        +timeout_seconds : int
    }

    class AiNodeConfig {
        +model : str
        +prompt : str
        +llm_config : LLMConfig
    }
    BaseNodeConfig <|-- AiNodeConfig

    class ToolNodeConfig {
        +tool_name : str
        +tool_args : dict
    }
    BaseNodeConfig <|-- ToolNodeConfig

    class NodeMetadata {
        +node_id : str
        +version : str
        +owner : str
        +created_at : datetime
        +duration : float
    }

    class NodeExecutionResult {
        +bool success
        +Any output
        +NodeMetadata metadata
        +UsageMetadata usage
    }

    class UsageMetadata {
        +int prompt_tokens
        +int completion_tokens
        +float cost
    }

    NodeExecutionResult o-- NodeMetadata
    NodeExecutionResult o-- UsageMetadata
```

---

## 4. ScriptChain Execution Levels & DAG

```mermaid
graph TD
    A1[Load Prompt] -->|level 0| A2[Detect Intents]
    A2 -->|level 1| B1[Fetch Domain Knowledge]
    A2 -->|level 1| B2[Generate Story Outline]
    B1 & B2 -->|level 2| C1[Compose Narrative]
    C1 -->|level 3| D1[Post-process]
    D1 -->|level 4| E1[Return JSON Response]
```

---

## 5. End-to-End Request Sequence (Chat Completion)

```mermaid
sequenceDiagram
    participant FE as Front-End
    participant API as FastAPI
    participant SC as ScriptChain
    participant AN as AiNode
    participant TS as ToolService
    participant LLM as OpenAI

    FE->>API: POST /v1/chat (messages[])
    API->>SC: build_and_execute()
    SC->>AN: execute(context)
    AN->>LLM: ChatCompletion (function-calling)
    LLM-->>AN: response (function_call name="db_query")
    AN->>TS: call_tool(db_query, sql="…")
    TS->>LLM: moderate sql (optional)
    TS-->>AN: query_results
    AN->>LLM: follow-up completion
    LLM-->>AN: assistant reply
    AN-->>SC: NodeExecutionResult
    SC-->>API: ChainExecutionResult
    API-->>FE: 200 OK (assistant reply)
```

---

## 6. Error & Retry Workflow (Node Timeout)

```mermaid
stateDiagram-v2
    [*] --> Running
    Running -->|timeout| Timeout
    Timeout --> RetryPending
    RetryPending -->|max_attempts<3| Running
    RetryPending -->|max_attempts>=3| Failed
    Failed --> [*]
```

---

### Legend
• *Rounded rectangles* = processes.  
• *Databases* = storage/persistence.  
• Dotted inheritance arrows depict "extends" relationships.  
• Colors and emojis hint at hosting environment but have no semantic meaning.

---
*Last updated: {{auto}}* 