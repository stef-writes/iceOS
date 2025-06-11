# Architecture & Workflow Documentation

> This document gives a birds-eye view of how our current ADK-based agent integrates (or will integrate) with MCP, what the internal runtime objects look like, and how requests flow from users all the way to external services.

---

## 1. High-level System Architecture

```mermaid
%%--------------------------------------------------
%% ADK Agent talking to an external MCP server
%%--------------------------------------------------
graph TD
    subgraph Client
        A[User / Front-end]
    end

    subgraph ADK_Runtime[iceOS-Beta01 ‑ ADK Runtime]
        B[FastAPI Endpoint] -->|JSON| C[ScriptChain]
        C --> D[ADK Agent]
        D --> E[InvocationContext]
        D --> F[Built-in Tools]
        D --> G[MCPToolset]
        C --> R[(Redis / Session Store)]
    end

    subgraph MCP_Server[Remote MCP Server]
        H[(Tool 1)]
        I[(Tool 2)]
        J[(Tool n)]
    end

    A -->|HTTP| B
    G -->|SSE / Stdio| MCP_Server
    G --> H
    G --> I
    G --> J
```

**Legend**  
• Boxes = processes/objects.  
• Rounded boxes = storage or persistent state.  
• Arrows = direction of request/response.

---

## 2. Core Runtime Data Models

Below are simplified (Python / Pydantic-like) schemas of the most critical ADK context objects.

```python
class InvocationContext(BaseModel):
    # Immutable per invocation
    invocation_id: str
    session: Session
    agent: "BaseAgent"

    # Mutable namespaces
    state: dict[str, Any]            # temp:/user:/app: keys
    user_content: ContentPartList    # initial user prompt

    # Helpers
    def save_artifact(name: str, content: Part): ...
    def load_artifact(name: str) -> Part: ...
```

```python
class ToolContext(InvocationContext):
    tool_name: str

    # Auth helpers
    def request_credential(config: AuthConfig): ...
    def get_auth_response(config: AuthConfig) -> Credentials: ...

    # Memory helpers
    def search_memory(query: str, top_k: int = 5) -> list[MemoryEntry]: ...
```

```python
class MCPToolset(BaseModel):
    server_params: StdioServerParameters | SseServerParameters
    tools: dict[str, BaseTool]

    async def call(tool_name: str, **kwargs) -> Any: ...
```

---

## 3. Process Workflows

### 3.1 Agent *as* MCP **Client**

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Agent
    participant MCP as MCPToolset
    participant Server as MCP Server

    User->>API: POST /v1/chat (prompt)
    API->>Agent: invoke_script_chain()
    Agent->>MCP: tools/list (discover)
    MCP->>Server: tools/list
    Server-->>MCP: tool definitions
    Agent->>MCP: tools/call: "database_query"
    MCP->>Server: tools/call(database_query)
    Server-->>MCP: JSON result
    MCP-->>Agent: result
    Agent-->>API: final response
    API-->>User: Chat completion
```

### 3.2 Exposing ADK Tool *as* MCP **Server**

```mermaid
flowchart LR
    subgraph FastMCP_Server
        T1[ADK Tool: load_web_page]
        T2[ADK Tool: summarize_pdf]
        FastMCP --> T1 & T2
    end

    ClientApp -- tools/list --> FastMCP_Server
    ClientApp -- tools/call(load_web_page) --> FastMCP_Server
    FastMCP_Server -->|Result| ClientApp
```

---

## 4. Hypothetical End-User Flow (Story Generator Example)

1. **User opens** the Story UI and enters: "Write a fantasy story about three heroes."
2. Front-end **POSTs** the prompt to `/api/v1/chains/execute`.
3. **ScriptChain** schedules nodes: `character_generator → story_generator → character_analysis → story_summarizer`.
4. During `character_analysis`, the LLM triggers a **function_call** → `word_count` (ADK tool).  A validation error occurs because the `text` field is missing.
5. The agent logs the error, skips downstream dependencies that require that output, but continues with nodes that can still run (`character_generator`).
6. Finally, the chain returns a partial story plus characters; the UI displays it.

```mermaid
stateDiagram-v2
    [*] --> PromptReceived
    PromptReceived --> ChainScheduled
    ChainScheduled --> CharacterGenerator
    CharacterGenerator --> StoryGenerator
    StoryGenerator --> CharacterAnalysis
    CharacterAnalysis -->|validation error| ErrorState
    ErrorState --> StorySummarizer : dependency missing
    StorySummarizer --> ResponsePackaged
    ResponsePackaged --> [*]
```

---

## 5. Next Steps

• Decide whether to start with *Client* integration (`MCPToolset`) or *Server* exposure (FastMCP).  
• Implement missing validation for `word_count` tool to eliminate current errors.  
• Harden state handling (graceful skips vs. retries) for multi-step chains. 