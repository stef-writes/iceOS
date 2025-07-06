## AI Testing Guide: Ensuring Quality Test Generation

### 1. Principles for AI-Generated Tests

- **Real Functionality Over Mocks**  
  Prefer testing real integrations (e.g., databases, APIs) over mocks when safe. Use mocks only for non-deterministic or external dependencies (e.g., third-party APIs).
- **Cover Critical Paths**  
  Focus on high-risk areas: error handling, edge cases, and core business logic.
- **Idempotency**  
  Tests should produce the same results when run repeatedly.
- **Readability**  
  Tests should be self-documenting (clear names, minimal setup).

---

### 2. Test Design Checklist

#### A. Nodes

- **Input Validation**  
  Test invalid inputs (e.g., missing fields, wrong types).
- **Output Sanity**  
  Verify outputs match schemas or expected formats.
- **Dependencies**  
  Test nodes with required tools or other nodes.

```python
@pytest.mark.asyncio
async def test_ai_node_invalid_input():
    node = AiNode(config=...)
    with pytest.raises(ValidationError):
        await node.execute({"wrong_input": "test"})
```

#### B. Tools

- **Core Functionality**  
  Test the tool's main operation with realistic inputs.
- **Error Cases**  
  Test tool failures (e.g., API timeouts, invalid permissions).
- **Idempotency**  
  For deterministic tools (e.g., `SumTool`), ensure repeated calls yield the same result.

```python
async def test_web_search_tool_rate_limiting():
    tool = WebSearchTool()
    with pytest.raises(RateLimitError):
        await tool.run(query="test")  # Assume rate-limited
```

#### C. Agents

- **Routing Logic**  
  Test agent decision-making (e.g., `RouterAgent` selecting the correct sub-agent).
- **Context Isolation**  
  Ensure agents don't leak state between runs.
- **Tool Integration**  
  Test agents calling tools with real inputs.

```python
async def test_agent_tool_integration():
    agent = FlowDesignAgent(tools=[WebSearchTool()])
    result = await agent.execute({"query": "iceOS"})
    assert "results" in result.output
```

#### D. Full Chains

- **End-to-End Flows**  
  Test chains with real nodes/tools (e.g., `AiNode → ToolNode`).
- **Error Recovery**  
  Verify fallback nodes or retries work.
- **Parallel Execution**  
  Test chains with concurrent nodes (if supported).

```python
async def test_chain_with_fallback_node():
    chain = ScriptChain(nodes=[failing_node, fallback_node])
    result = await chain.execute({...})
    assert result.output == "fallback_output"
```

#### E. CLI

- **Command Success**  
  Test happy paths (e.g., `ice chain run demo_chain`).
- **File I/O**  
  Verify CLI-generated files (e.g., exports, logs).
- **Error Messages**  
  Test invalid commands or inputs.

```python
def test_cli_chain_export(tmp_path):
    output_file = tmp_path / "output.json"
    result = runner.invoke(cli, ["chain", "export", "demo_chain", str(output_file)])
    assert output_file.exists()
```

---

### 3. Validation Steps for AI-Generated Tests

1. **Manual Review**  
   Check for over-mocking, redundant tests, and unclear assertions.
2. **Coverage Reports**  
   Use `pytest-cov`; aim for 70%+ coverage on high-risk modules.
3. **CI Integration**  
   Run tests in CI with real dependencies; fail-fast on flaky tests.
4. **Flakiness Detection**  
   Rerun tests multiple times to catch non-deterministic behavior.

---

### 4. Anti-Patterns to Avoid

- **Mock Everything** — tests become brittle and don't reflect real behavior.
- **Testing Trivial Code** — avoid testing getters/setters or library code.
- **Overly Complex Fixtures** — keep test setup minimal and reusable.

---

### 5. Example Workflow for AI-Generated Tests

1. **Prompt the AI**  
   *"Generate a test for `ToolNode` with a real `EchoTool` and validate output."*
2. **Review Output**  
   Ensure the test uses real tools (not mocks) and covers edge cases.
3. **Refine**  
   Add missing cases (e.g., error handling) or simplify fixtures.

---

### 6. Tools to Enforce Quality

| Tool | Purpose |
|------|---------|
| `pytest` | Test execution and assertions |
| `pytest-cov` | Coverage reporting |
| `hypothesis` | Property-based testing |
| `tox` | Multi-environment testing |
| `respx` / `pytest-mock` | Mocking (use sparingly) |

---

### Next Steps

1. **Implement** — apply this guide to existing tests (e.g., refactor mocked tests).
2. **Automate** — add CI checks for coverage and flakiness.
3. **Iterate** — continuously refine tests based on bugs or gaps. 