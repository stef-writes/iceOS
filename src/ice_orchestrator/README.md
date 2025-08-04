# ice_orchestrator – Workflow Execution Engine

## Overview

`ice_orchestrator` is the runtime execution engine for iceOS workflows. It orchestrates the execution of nodes, manages runtime dependencies, and provides all runtime services including agents, memory, LLM providers, and context management.

**🎯 Core Responsibilities**
* **Workflow Execution** – DAG-based workflow orchestration with parallel execution
* **Agent Runtime** – Execution of autonomous agents with tool access and memory
* **Memory Management** – Working, episodic, semantic, and procedural memory systems
* **LLM Services** – Provider integrations (OpenAI, Anthropic, Gemini, DeepSeek)
* **Context Management** – Runtime context, state persistence, and data flow
* **Node Execution** – Built-in executors for all node types (tool, LLM, agent, etc.)
* **Error Handling** – Resilient execution with configurable failure policies



..........