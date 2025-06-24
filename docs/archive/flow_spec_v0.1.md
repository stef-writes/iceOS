# FlowSpec v0.1 – Draft (Archived)

> This document has been moved to `docs/archive/` to reduce surface area of the active documentation set. It remains here for historical reference only.

---

<!-- Original content below -->

# FlowSpec v0.1 – Draft

> Canonical JSON representation of an iceOS workflow (single-file, portable).

Status: **DRAFT** – introduced in Sprint 1. Breaking changes require schema_version bump.

---

## 1. Top-Level Shape

```jsonc
{
  "schema_version": "0.1",    // semantic
  "id": "flow_abc123",        // UUIDv4
  "name": "Slack BTC Alert",
  "nodes": [ /* Node objects */ ],
  "edges": [ /* Edge objects */ ],
  "ui":   { /* optional front-end hints */ }
}
```

---

## 2. Node Object

Common fields (shared by all node types):

| Key            | Type                | Required | Notes |
|----------------|---------------------|----------|-------|
| id             | string (uuid4)      | ✓        | Unique within flow |
| type           | "ai" \| "tool" \| "condition" | ✓ | Discriminator |
| name           | string              | –        | Human readable |
| dependencies   | string[]            | –        | IDs of upstream nodes |
| input_mappings | object              | –        | Placeholder → {source_node_id, source_output_key} |
| input_schema   | object \| $ref       | –        | Same as NodeConfig |
| output_schema  | object \| $ref       | –        | 〃 |
| provider       | enum(ModelProvider) | –        | If relevant |

### 2.1 ai
Additional:
| key | type | description |
|-----|------|-------------|
| model | string | e.g. gpt-4o |
| prompt | string | template |
| llm_config | object | temperature, etc. |
| tools | ToolConfig[] | optional |

### 2.2 tool
Additional:
| key | type |
|-----|------|
| tool_name | string |
| tool_args | object |

### 2.3 condition
Additional:
| key | type | description |
|-----|------|-------------|
| expression | string | Python-eval or JMESPath, evaluated against assembled ctx |
| true_branch | string[] | Downstream node IDs active when expression truthy |
| false_branch | string[] | Optional |

---

## 3. Edge Object

Until loops are supported, edges are implicit via `dependencies` on nodes. Future versions will allow explicit metadata per edge (condition labels, side-effect risk, etc.).

---

## 4. UI Block (optional)

```jsonc
"ui": {
  "positions": { "node_id": {"x": 200, "y": 120} },
  "comments":  { "node_id": "Some sticky note" },
  "colors":    { "node_id": "#FFAA00" }
}
```

None of these attributes impact execution – safe to omit.

---

## 5. Extensibility Guidelines

1. Additive only within `0.x` minor bumps (new optional fields).
2. Removing or changing meaning requires `schema_version` major bump.
3. Front-end must ignore unknown keys.

---

### Appendix A – JSON Schema Location

The machine-readable JSON-Schema lives at `schemas/flow_spec_v0.1.json` and is enforced in CI by `scripts/check_flow_spec.py`. 