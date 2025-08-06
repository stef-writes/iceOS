# iceOS Example Workflows

This directory contains comprehensive example workflows that demonstrate iceOS in action. These examples showcase real-world e-commerce automation using the complete iceOS stack: workflow orchestration, tool execution, loop processing, and result aggregation.

## 🚀 Quick Start

All examples use offline-friendly test mode by default. Run any example from the project root:

```bash
# Direct workflow creation
python examples/seller_assistant_direct.py

# Fluent API workflow building  
python examples/seller_assistant_fluent.py

# Debug/minimal testing
python examples/debug_serialization.py

# Live OpenAI integration (requires API key)
export OPENAI_API_KEY="sk-..."
python examples/seller_assistant_live.py
```

## 📋 Example Workflows

### 1. Seller Assistant (Direct) - `seller_assistant_direct.py`

**What it does**: Comprehensive e-commerce workflow that loads products from CSV, processes each through pricing and copywriting, and aggregates results.

**Architecture**: Direct NodeConfig creation showing explicit workflow construction.

**Key Features**:
- CSV data ingestion (9 sample products)
- Loop processing with dependency management  
- Tool composition (pricing → copywriting → marketplace simulation)
- Result aggregation with success/failure tracking

**Output**:
```json
{
  "load_csv": { "rows": [...] },
  "process_loop": [
    {
      "listing_id": "TEST-refrigerator-690ebf",
      "title": "TEST Refrigerator", 
      "description": "Test listing for Refrigerator",
      "price": 750.0
    }
    // ... 8 more items
  ],
  "aggregate": {
    "total": 9,
    "success": 9, 
    "failures": 0,
    "items": [...]
  }
}
```

### 2. Seller Assistant (Fluent) - `seller_assistant_fluent.py`

**What it does**: Same functionality as direct example, but demonstrates the fluent workflow building API.

**Architecture**: Shows how to construct workflows programmatically with clean node creation and dependency management.

**Key Learning**: Demonstrates proper workflow construction patterns and node dependency resolution.

### 3. Seller Assistant (Live) - `seller_assistant_live.py`  

**What it does**: Production-ready version that calls real OpenAI APIs for title/description generation.

**Requirements**: 
- Valid `OPENAI_API_KEY` environment variable
- Network connectivity

**Safety**: No external marketplace uploads (`upload=False`) - only OpenAI calls.

**Usage**:
```bash
export OPENAI_API_KEY="sk-your-key-here"
python examples/seller_assistant_live.py
```

### 4. Debug Serialization - `debug_serialization.py`

**What it does**: Minimal single-node workflow for debugging serialization and execution issues.

**Use Case**: Troubleshooting tool registration, context management, or workflow validation problems.

## 🛠️ Technical Architecture

### Workflow Components

1. **CSV Loader** (`csv_loader` tool)
   - Loads product data from local CSV file
   - Converts rows to JSON objects for processing
   - Dependency-free using Python's built-in `csv` module

2. **Loop Processor** (`LoopNodeConfig`)
   - Iterates over CSV rows with `items_source: "load_csv.rows"`
   - Executes `listing_agent` tool for each product
   - Collects results into output array

3. **Listing Agent** (`listing_agent` tool)
   - Composite tool orchestrating pricing, copywriting, marketplace upload
   - Pricing: Applies margin calculation with rounding
   - Copywriting: Generates titles/descriptions (test mode or real LLM)
   - Marketplace: Simulates upload with deterministic test IDs

4. **Aggregator** (`aggregator` tool)
   - Summarizes loop results into totals and success/failure counts
   - Receives results via template resolution: `"results": "{{ process_loop }}"`
   - Outputs comprehensive metrics for monitoring

### Data Flow & Context Propagation

The iceOS DAG workflow orchestrator handles automatic context propagation:

```
load_csv (Level 0)
    ↓ (provides: rows)
process_loop (Level 1) 
    ↓ (provides: array of listing results)
aggregate (Level 2)
    ↓ (provides: summary metrics)
```

**Key Insight**: Template resolution `{{ process_loop }}` automatically resolves to the actual loop output array through the dependency graph context management.

### Error Handling & Resilience

- **Graceful Degradation**: Individual tool failures don't crash the entire workflow
- **Retry Policies**: Configurable retry with exponential backoff
- **Validation**: Schema validation for all inputs/outputs with detailed error messages
- **Test Mode**: All tools support offline operation for development/testing

## 🔧 Tool Registration & Discovery

Tools are auto-registered via toolkit imports:

```python
import ice_tools
from ice_tools.toolkits.ecommerce import EcommerceToolkit

# Register toolkit with configuration
EcommerceToolkit(test_mode=True, upload=False).register()
```

Available tools:
- `csv_loader`: File ingestion with configurable delimiters
- `pricing_strategy`: Cost → price calculation with margin & rounding
- `title_description_generator`: LLM-powered copywriting (test/live modes)
- `marketplace_client`: HTTP API client for external marketplaces
- `listing_agent`: Composite orchestrator combining above tools
- `aggregator`: Result summarization and metrics

## 📊 Sample Data

Included CSV contains realistic product data:

| Product/Item | Suggested Price | Description |
|-------------|----------------|-------------|
| Refrigerator | $600.00 | Scratched, Stainless, 2 Door w/ Water |
| Infared Heating Panel | $100.00 | 2x2' |
| Tile | $300 per cs | 5 cases Large Tile, Calcutta Rustico |
| ... | ... | ... |

**9 total products** demonstrating various price formats, descriptions, and product categories.

## 🚨 Common Issues & Solutions

### Issue: Empty aggregation results
**Cause**: Tool input schema filtering  
**Solution**: Override `get_input_schema()` in tools using `**kwargs` to explicitly declare expected parameters

### Issue: Template resolution not working
**Cause**: Context cleaning or dependency ordering  
**Solution**: Verify dependency relationships and check DAG level assignment

### Issue: Individual tool failures in loops
**Cause**: Missing metadata fields in NodeExecutionResult  
**Solution**: Ensure all NodeMetadata constructors include required fields (owner, description, provider)

## 🌟 Best Practices

1. **Use Test Mode First**: Always develop with `test_mode=True` before enabling real API calls
2. **Explicit Dependencies**: Clearly declare node dependencies for proper execution ordering  
3. **Schema Validation**: Override input schemas for tools accepting dynamic parameters
4. **Error Monitoring**: Check both individual node success and overall workflow completion
5. **Incremental Development**: Start with single tools, then compose into workflows

## 📚 Next Steps

- **Blueprint YAML**: Explore declarative workflow definition in `blueprints/seller_assistant.yaml`
- **Custom Tools**: Create domain-specific tools following the ecommerce toolkit patterns
- **Production Deployment**: Configure real API keys and marketplace endpoints
- **Monitoring**: Integrate with observability tools for production workflows

---

These examples demonstrate iceOS as a production-ready workflow orchestration platform with real-world applicability in e-commerce automation, data processing, and LLM-powered applications.