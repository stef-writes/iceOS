### Runtime Node Types → Configs → Executors

Canonical mapping of node types to their Pydantic configs and orchestrator executors. Source of truth: `ice_core.models.enums.NodeType`, `ice_core.utils.node_conversion._NODE_TYPE_MAP`, and executor modules under `ice_orchestrator/execution/executors/builtin/`.

| NodeType | Config (ice_core.models) | Executor (ice_orchestrator) |
|---|---|---|
| tool | `ToolNodeConfig` | `execution/executors/builtin/tool_node_executor.py` |
| llm | `LLMNodeConfig` | `execution/executors/builtin/llm_node_executor.py` |
| agent | `AgentNodeConfig` | `execution/executors/builtin/agent_node_executor.py` |
| condition | `ConditionNodeConfig` | `execution/executors/builtin/condition_node_executor.py` |
| workflow | `WorkflowNodeConfig` | `execution/executors/builtin/workflow_node_executor.py` |
| loop | `LoopNodeConfig` | `execution/executors/builtin/loop_node_executor.py` |
| parallel | `ParallelNodeConfig` | `execution/executors/builtin/parallel_node_executor.py` |
| recursive | `RecursiveNodeConfig` | `execution/executors/builtin/recursive_node_executor.py` |
| code | `CodeNodeConfig` | `execution/executors/builtin/code_node_executor.py` |
| human | `HumanNodeConfig` | `execution/executors/builtin/human_node_executor.py` |
| monitor | `MonitorNodeConfig` | `execution/executors/builtin/monitor_node_executor.py` |
| swarm | `SwarmNodeConfig` | `execution/executors/builtin/swarm_node_executor.py` |

Notes
- All runtime behavior is implemented via executors; the orchestrator should not have separate top-level node packages.
- Node conversion is centralized in `_NODE_TYPE_MAP`; executors are auto-registered via `@register_node`.

LLM clarity
- LLM at runtime is just the `llm` node type executed by `llm_node_executor`. There is no separate SDK "operator" class anymore.
- Configuration: `ice_core.models.llm.LLMConfig` holds provider/model/runtime parameters. The node’s `LLMNodeConfig` references or embeds it.
- Providers: `ice_core/llm/providers/*` implement provider handlers consumed by `LLMService`.
- Prompting: provide prompts via node config/blueprints; executors render and call the provider through `LLMService`.

Testing notes
- Offline tests should register an echo LLM factory under `gpt-4o`:
  ```python
  from ice_core.unified_registry import register_llm_factory
  register_llm_factory("gpt-4o", "scripts.verify_runtime:create_echo_llm")
  ```
- If a blueprint omits an explicit LLM output schema, runtime defaults to `{ "text": "string" }` during validation.
- Tools can be loaded via plugin manifests using `ICEOS_PLUGIN_MANIFESTS`; the registry is idempotent and safe across multiple loaders.

Breaking changes
- `LLMOperatorConfig` has been renamed to `LLMNodeConfig`. Update imports and JSON schema references accordingly (`node_configs/LLMNodeConfig.json`).
