# Model Selection Guide for Frosty Blueprint Generation

Based on benchmark comparisons and real-world performance data (as of 2024):

## Best Models by Task

### 1. Intent Parsing & Understanding
- **Primary**: GPT-4o (MMLU: 88.7%, strong instruction following)
- **Alternative**: Claude 3.5 Sonnet (MMLU: 89.3%, excellent at nuanced understanding)
- **Budget**: DeepSeek-V3 (MMLU: 88.5%, 42x cheaper than Claude)

### 2. Planning & Reasoning
- **Primary**: DeepSeek-R1 (specialized for reasoning tasks)
- **Alternative**: o1-preview (when available, best-in-class reasoning)
- **Budget**: DeepSeek-V3 (includes R1 reasoning capabilities)

### 3. Code Generation
- **Primary**: Claude 3.5 Sonnet (HumanEval: 93.7%, best for code)
- **Alternative**: GPT-4o (strong general coding, good library knowledge)
- **Budget**: DeepSeek-V3 (HumanEval: 82.6%, excellent price/performance)
- **NOT Recommended**: Claude 3 Haiku (75.9% - significantly lower than alternatives)

### 4. Diagram Generation (Mermaid)
- **Primary**: GPT-4o (best at structured output formats)
- **Alternative**: Claude 3.5 Sonnet (excellent formatting adherence)
- **Budget**: DeepSeek-V3 (good structured output)

### 5. Tool Creation & API Integration
- **Primary**: GPT-4o (extensive API/library knowledge)
- **Alternative**: Claude 3.5 Sonnet (excellent at following specifications)

## Price Comparison (per million tokens)

| Model | Input Cost | Output Cost | Notes |
|-------|------------|-------------|-------|
| DeepSeek-V3 | $0.14 | $0.28 | Best value, open source |
| GPT-4o Mini | $0.15 | $0.60 | Good for simple tasks |
| Claude 3 Haiku | $0.25 | $1.25 | Fast but limited |
| Claude 3.5 Sonnet | $3.00 | $15.00 | Best for complex code |
| GPT-4o | $5.00 | $15.00 | Most versatile |

## Recommended Configuration

For production use with cost optimization:
```python
providers = {
    "intent": "deepseek-v3",        # Good enough for intent
    "planning": "deepseek-r1",       # Specialized for reasoning
    "decomposition": "deepseek-v3",  # Cost-effective
    "diagram": "deepseek-v3",        # Handles structure well
    "code": "claude-3.5-sonnet",     # Worth the cost for quality code
}
```

For maximum quality (cost no object):
```python
providers = {
    "intent": "claude-3.5-sonnet",
    "planning": "o1-preview",         # When available
    "decomposition": "gpt-4o",
    "diagram": "gpt-4o", 
    "code": "claude-3.5-sonnet",
}
```