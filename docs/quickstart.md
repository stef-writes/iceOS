# Quick-Start

> **Goal:** run a live, multi-agent workflow in < 5 minutes.

## 1. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Export API keys
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=AIza...
export DEEPSEEK_API_KEY=sk-...
```
Only the providers you intend to call must be set.

## 3. Hello-World agent
Run the bundled script:
```bash
python scripts/test_agent_flow.py
```
Expected output:
```text
Agent success:  True
Agent output :  {'word_count': 7, 'text': 'Hello world from our new agent framework!'}
```

## 4. Full system demo
```bash
python scripts/test_complex_system.py
```
This will:
1. Build 7 nodes (4 LLM, 3 tools).  
2. Wrap them in a `LevelBasedScriptChain` → `WorkflowAgentAdapter`.  
3. Register additional single-node agents.  
4. Ask the `RouterAgent` (powered by OpenAI) to decide which agent handles the query.

Sample log excerpt:
```text
Router chose success: True
Output: { ... }
Session outputs keys: dict_keys(['openai_agent'])
```

## 5. Next steps
* Explore the code in `src/app/agents` and `src/app/chains`.
* Check the Architecture docs for design details.
* Build your own tool under `app/tools/builtins/` and register it. 