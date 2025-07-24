# iceOS Examples

This directory contains the **comprehensive demo** that showcases all iceOS capabilities in a single, well-documented example.

## 🚀 Quick Start

```bash
# 1. Start the iceOS server
make dev

# 2. Run the comprehensive demo
python examples/comprehensive_demo.py
```

## 📚 What's Included

The `comprehensive_demo.py` showcases:

### Section 1: Incremental Blueprint Construction
Shows how Frosty can build workflows step-by-step:
- Start with empty blueprint
- Add nodes incrementally
- Get AI suggestions for next steps
- Validate as you go
- Finalize when ready

### Section 2: Cost Estimation
Demonstrates pre-execution cost analysis:
- Token usage estimates
- API call predictions
- Duration forecasts
- Cost breakdown by node

### Section 3: Event Streaming
Real-time execution monitoring:
- Workflow lifecycle events
- Node start/complete notifications
- Progress tracking
- Error handling

### Section 4: Debug & Monitoring
Troubleshooting and optimization:
- Execution summaries
- Performance metrics
- Bottleneck identification
- Optimization suggestions

### Section 5: Nested Workflows
Composition and reusability:
- Creating workflow components
- Nesting workflows
- Data flow between levels
- Clean abstractions

## 🎯 Using Individual Sections

Each section is self-contained and can be copied for specific use cases:

```python
# Just want incremental construction?
await section_1_incremental_construction()

# Just need cost estimation?
cost = await section_2_cost_estimation(blueprint_id)

# Just want event streaming?
run_id, events = await section_3_event_streaming(blueprint_id)
```

## 📊 Sample Data

The demo automatically creates sample data at `examples/data/sales_data.csv` if it doesn't exist.

## 🧪 Golden Test Files

The `golden/` directory contains test fixtures used by the integration tests. These ensure backward compatibility as the platform evolves.

## 🔧 Prompt Templates

The `prompt_templates/` directory contains reusable prompt templates that can be referenced in blueprints.

## 🏗️ Architecture

```
comprehensive_demo.py
├── Section 1: Build blueprint incrementally (like Frosty)
├── Section 2: Estimate costs before running
├── Section 3: Execute with real-time events
├── Section 4: Debug and monitor execution
└── Section 5: Compose nested workflows
```

## 💡 Key Concepts Demonstrated

1. **Partial Blueprints** - Build workflows incrementally
2. **Cost Transparency** - Know costs before execution
3. **Real-time Feedback** - Stream events during execution
4. **Debugging Tools** - Understand what happened and why
5. **Composability** - Build complex from simple

## 🚦 Prerequisites

- Python 3.8+
- iceOS server running (`make dev`)
- Rich library (`pip install rich`)

## 📝 Notes

- The demo uses simulated data for some features that aren't fully implemented yet
- Each section prints clear output showing what's happening
- Error handling demonstrates graceful failures
- The code is extensively commented for learning

---

This comprehensive demo replaces the previous scattered examples with a single, cohesive demonstration of iceOS capabilities. 