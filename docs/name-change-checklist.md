# Naming Migration Guide

Thinking about renaming pieces of the framework?  Use this checklist so IDE refactors and docs stay in sync.

| Current term | Proposed | Impacted modules/files | Notes |
|--------------|----------|------------------------|-------|
| Node         | *Kernel* / *Skill* | `src/app/nodes/*`, types `AiNodeConfig`, `ToolNodeConfig`, factory | Public API, plugin registry label. Provide alias class to avoid breaking import paths. |
| ToolService  | *SkillHub*        | `ice_sdk/tool_service.py`, any direct imports | Rename class + update re-export in `ice_sdk.__init__`. Keep old name as deprecated alias for one release. |
| LevelBasedScriptChain | *Workflow* | `app/chains/orchestration/*` | Rename module + class; adapters already call via import path. |
| AgentAdapter | *KernelAgent* (if Node→Kernel) | `app/agents/node_agent_adapter.py` | Simple rename + re-export under old name. |
| WorkflowAgentAdapter | *WorkflowAgent* | `app/agents/workflow_agent_adapter.py` | Same as above. |
| GraphContextManager | *ContextStore* | `app/utils/context/manager.py` | Update `__all__` and docs. |

Migration steps
1. **Decide vocabulary** – fill the "Proposed" column.  
2. Run automated rename with IDE or `sed`, respecting camel-case vs snake-case.  
3. Add deprecated aliases:  
   ```python
   class Node(Kernel):
       pass  # TODO: remove in v1.1
   ```
4. Update docs search-and-replace (`docs/`) – make sure Mermaid diagrams mention new names.
5. Bump version (`pyproject.toml`) and write a changelog entry.

---
> Tip: keep at least one minor release where old names work via aliases; announce removal schedule in README. 