# iceOS Chain Composition Roadmap

## Vision Statement
*Enable fluid composition of AI capabilities through nested, agentic workflows that maintain iceOS's rigor while empowering:*
- **Developers** to build complex reasoning systems via simple node connections
- **AI Agents** to dynamically assemble tools based on context
- **Systems** to scale through recursive workflow nesting

---

## Milestone 1: Core Composition Engine (Q3 2024)

### Objective
Establish foundational ability to treat chains as nodes

### Key Components
1. **Chain-as-Node Specification**
```yaml
{
  "type": "chain",
  "chainDefinition": {
    "$ref": "flow_spec_v0.1.json"
  },
  "inputMapping": {
    "sourceParam": "targetChain.inputSlot"
  }
}
```

2. **Execution Orchestrator**
```python
class CompositeNode(Node):
    def resolve(self):
        return unpack_chain(self.chain_definition)  # New resolution logic

    async def execute(self):
        subchain_result = await ScriptChain(
            self.chain_definition
        ).execute(self.inputs)
        return map_outputs(subchain_result, self.output_spec)
```

3. **CLI Support**
```bash
ice chain:create reasoning_flow --type composite
ice chain:add-node reasoning_flow agentic_subflow --as-node
```

---

## Milestone 2: Dynamic Agent-Tool Binding (Q4 2024)

### Objective
Enable runtime tool attachment to agent nodes

### Implementation Strategy
1. **Tool Registry Extension**
```python
class NodeRegistry:
    def get_tools_for_agent(self, agent_id: str):
        return [
            t for t in self._tools
            if t.metadata.agent_bindable
        ]
```

2. **Agent Node Enhancement**
```python
class AgentNode(BaseNode):
    def attach_tool(self, tool_name: str):
        if tool_name not in self.available_tools:
            raise ToolBindingError(f"Tool {tool_name} not available")
        self.active_tools.append(
            self.registry.get_tool(tool_name)
        )
```

3. **Example Workflow**
```yaml
nodes:
  - id: analysis_agent
    type: agent
    config:
      tools:
        - web.search
        - data.analyze
        - math.stats
```

---

## Milestone 3: Recursive Scaling (Q1 2025)

### Objective
Support arbitrary-depth nesting of reasoning flows

### Critical Path
1. **Execution Context Stack**
```python
class ExecutionStack:
    def push_context(self, chain_id: str):
        self.stack.append(
            WorkflowContext(
                parent=self.current_context
            )
        )

    def pop_context(self):
        return self.stack.pop()
```

2. **Cross-Chain Debugging**
```python
def annotate_log_with_chain_stack():
    return {
        "chain_stack": [
            c.name for c in execution_stack.stack
        ]
    }
```

3. **Performance Optimization**
```python
class NestedChainProfiler:
    def report_metrics(self):
        return {
            "total_nodes": sum(
                len(c.nodes) for c in self.chain_stack
            ),
            "cross_chain_latency": self._measure_boundary_transitions()
        }
```

---

## Testing Strategy

### Unit Tests
```python
async def test_3_level_nesting():
    root_chain = load_chain("root.yaml") 
    result = await root_chain.execute({})
    assert result.depth == 3
    assert "subchain_1.subchain_2.final_output" in result.outputs
```

### Property Tests
```python
@given(st.integers(min=1, max=5))
def test_chain_depth_properties(depth):
    chain = generate_nested_chain(depth)
    assert chain.max_depth == depth
```

---

## Vision Alignment Table

| Capability          | Developer Value                          | System Property                  |
|---------------------|------------------------------------------|-----------------------------------|
| Nested Chains       | Build complex systems incrementally      | Maintain execution observability |
| Dynamic Tool Binding| Rapid experimentation cycle              | Enforce capability isolation      |
| Recursive Scaling   | Handle enterprise-grade workflows        | Control resource allocation       |

---

*This living document is the single source of truth for chain composition in iceOS. Update as features evolve to ensure alignment with the platform vision.* 

---

# CLI & Developer Experience Roadmap

The CLI is the **primary touch-point** for developers until GUI layers arrive. It must make every roadmap milestone above *tangible* within seconds.

## Guiding Principles
* **Three-Layer Rule**  
  1. Auto-generated SDK parity (thin wrappers)  
  2. Chain / Node / Edge domain verbs  
  3. UX polish (Rich, Typer, completions, Studio TUI)
* Async + Pydantic everywhere; side-effects live only inside Tool implementations.
* CLI mirrors SDK → SDK remains the single source of truth.
* No foot-guns: every mutating command supports `--dry-run` / `--yes`.

## Architecture Snapshot
```
SDK Core  (Pydantic + OpenAPI)
  │  code-gen
  ▼
Layer 0  Parity        ice <resource> <action>
  │  compose / specialise
  ▼
Layer 1  Domain        chain / node / edge
  │  polish
  ▼
Layer 2  UX            Rich output + Studio TUI
```

## 12-Week Delivery Schedule

| Phase | Week | Headline                  | Ships & Demo Value |
|-------|------|---------------------------|--------------------|
| 0     | 0    | **Groundwork**            | Binary scaffold, global flags, completions |
| 1     | 1-2  | **SDK Parity Alpha**      | Core resources (jobs, models, envs) |
| 2     | 3-4  | **Chains Exist**          | `chain create|list|get`, YAML persistence |
| 3     | 5-6  | **Nodes + Edges MVP**     | `node add`, `edge add`, lint, ASCII graph *(experimental flag)* |
| 4     | 7    | **Tool Ecosystem**        | `tool create`, attach/detach, built-ins pack |
| 5     | 8-9  | **Run & Observe**         | `chain run --watch`, logs follow, stats |
| 6     | 10   | **Guardrails & Tests**    | `chain guard`, `chain test`, CI-friendly exits |
| 7     | 11   | **Chain Studio (TUI)**    | Visual builder, REPL, attack mode |
| 8     | 12   | **DX Polish & Launch**    | Homebrew/PyPI, docs, screen-cast demo |

### Current Progress (2025-07-02)
* ✅ Global CLI context + core flags (`--json`, `--dry-run`, `--yes`, `--verbose`).
* ✅ Telemetry event bus + webhook wiring.
* 🚧 Phases 1-2 in active development (`chain create`, `node add`, YAML persistence).

## Feature Checklist (Trimmed to Demo-Critical)
* 80 % commands code-generated via OpenAPI → Typer.
* **F5-Wow Path**: `ice chain wizard` → `ice chain run --watch`.
* ASCII graphs (+ `--mermaid` diagrams) for quick visual feedback.
* Safety: `--dry-run`, `--watch`, undo log (`~/.ice/ops.log`).

## Developer Interface Milestone (Minimal Viable Set)
| Command | Impact |
|---------|--------|
| `ice chain:compose` | Compose & persist nested chains (demo hero flow) |
| `ice node:attach-tool` | Live agentic flexibility |
| `ice workflow:visualize` | Render ASCII / Mermaid graph |

---

# Interactive Chain Builder (Wizard)

> Status: **In Progress** (ships as part of CLI Phase 2)

The Builder offers a question-driven path from idea → runnable chain in under **3 minutes**.

## Architecture Layers
| Layer | Responsibility | Notes |
|-------|----------------|-------|
| IO layer | Prompt/collect answers (Typer + Questionary) | Copilot or GUI can swap this later |
| Builder-Engine | Stateless state-machine → `ChainDraft` | `ice_cli.chain_builder.engine` |
| Template layer | `ChainDraft` → `NodeConfig` + Python scaffold | Re-uses template helpers |

## Question Catalogue (v0)
1. **Chain meta** – name, `persist_interm_outputs`  
2. **Node loop** – node type, id, deps, type-specific extras, advanced opts  
3. **Review** – Mermaid graph + summary → confirm / write / run

## Milestones
| M# | Scope | ETA |
|----|-------|-----|
| **M0** | Linear graphs, `ai`+`tool` nodes, ≤10 nodes | 1 week |
| **M1** | Mermaid preview, validation (dup IDs, cycles) | +3 days |
| **M2** | REST façade for Copilot | +1 week |
| **M3** | Branching, `condition` / `sink` nodes, YAML import | +2 weeks |

## Success Criteria for Investor / Client Demo
```yaml
success_criteria:
  - "User creates nested chain in <3 mins"
  - "Live attach/detach of tools during demo"
  - "Visible pulse: nodes light up as executed"
  - "Recursive error: 'Chain depth 3' appears in logs"
```

---

# Cut-Smart Guidance
* **Must-haves for public beta** → CLI Phases 0-2 + Wizard M0-M1.
* Nice-to-have but drop-able if timeline slips: TUI, plugin market, undo logs.

---

# Webhook Event Integration (For Observability)
CLI commands SHOULD emit structured events (`cli.<command>.<status>`) so other subsystems can react.

```python
class CLICommandEvent(BaseModel):
    command: str
    status: Literal["started", "completed", "failed"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    params: dict[str, Any] = Field(default_factory=dict)
```

Emission:
1. **started** – before side-effects  
2. **completed** – on clean exit  
3. **failed** – on exception path

---

_Last consolidated_: 2025-07-02 by `Cursor AI` 