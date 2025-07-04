# Workflow Specification Template

_Use this document to fully describe a ScriptChain / multi-network workflow **and** its individual nodes. Duplicate & fill for each new flow._

---

## A. Workflow Overview

| Field | Value |
|-------|-------|
| **Workflow Name** | {{FLOW_NAME}} |
| **Author / Team** | {{AUTHOR}} |
| **Version** | {{SEMVER}} |
| **Last Updated** | {{YYYY-MM-DD}} |
| **Primary Objective** | {{BUSINESS_OBJECTIVE}} |
| **Success KPI** | {{KPI}} |
| **Deployment Tier** | Dev / Staging / Prod |

### A.1 Narrative
> {{PARAGRAPH describing what the workflow accomplishes and why it matters.}}

### A.2 Networks & Topology
| Network | Node Sequence | Purpose |
|---------|---------------|---------|
| Planning | idea_planner → research_planner → … | … |
| Research | … | … |

(Embed Mermaid diagram below if helpful.)

```mermaid
{{FLOW_DIAGRAM}}
```

### A.3 Requirements & Dependencies

#### External Keys
| Env Var | Purpose |
|---------|---------|
| `OPENAI_API_KEY` | GPT-4o calls |
| … | … |

#### Python Packages
```toml
openai = "^1.3.8"
anthropic = "^0.25.0"
httpx = "^0.27.0"
```

### A.4 Success Criteria
1. **Functional** – {{DETAILS}}
2. **Quality** – {{DETAILS}}
3. **Performance** – {{DETAILS}}
4. **Compliance** – {{DETAILS}}

### A.5 Governance & Compliance (Workflow-level)
| Aspect | Details |
|--------|---------|
| Data Classification | Public / Internal / Restricted |
| PII Processed? | Yes / No |
| Retention Policy | {{RETENTION_RULES}} |
| Regulatory Scope | GDPR / CCPA / SOC-2 |

---

## B. Node Specifications

_Copy the template below for **each** node and fill the placeholders._

### B.X Node: `{{NODE_ID}}`

#### 1. Identification
| Field | Value |
|-------|-------|
| Node ID | `{{NODE_ID}}` |
| Human Name | {{NODE_NAME}} |
| Network | {{NETWORK}} |
| Type | ai / tool / condition |

#### 2. Purpose
> {{ONE-SENTENCE_DESCRIPTION}}

#### 3. Model / Tool Details
| Property | Value |
| Provider | openai / anthropic / deepseek |
| Model | gpt-4o / claude-3-opus / deepseek-v3 |
| Temperature | {{TEMP}} |
| Top-p | {{TOP_P}} |
| Max Tokens | {{MAX_TOKENS}} |
| Function-Calling Enabled? | Yes/No |
| Token Budget | {{TOKENS_IN}} ⭢ {{TOKENS_OUT}} |

#### 4. Prompt / Command Template (AI nodes)
```text
SYSTEM:
{{SYSTEM_PROMPT}}

USER:
{{USER_SECTION}}
```

#### 5. I/O Schemas
_Input and output JSON schema or Pydantic models._

#### 6. Input Mappings
| Placeholder | Source Node | Source Key |
|-------------|------------|-----------|

#### 7. Operational Controls & Limits
| timeout_seconds | {{TIMEOUT}} |
| retries | {{RETRIES}} |
| backoff_seconds | {{BACKOFF}} |
| use_cache | true / false |
| Cost Budget (USD) | {{BUDGET}} |

#### 8. Failure & Fallback
Describe fallback behaviour.

#### 9. Observability
| Event Name | `{{SOURCE}}.{{verb}}` |
| Metrics | duration, tokens, cost |
| Logs | INFO / WARNING / ERROR |

#### 10. Test Coverage
| Test File | `tests/nodes/test_{{NODE_ID}}.py` |
| Assertions | schema, cost ceiling, deterministic fields |

#### 11. Governance & Compliance (Node-level)
| PII? | Yes / No |
| Data Classification | Public / Internal / Confidential |

#### 12. Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|

#### 13. Rollback & Recovery
Outline rollback triggers and procedures.

#### 14. Revision History
| Date | Author | Change |
|------|--------|--------|
| {{DATE}} | {{NAME}} | Initial spec |

---

*End of workflow template.* 