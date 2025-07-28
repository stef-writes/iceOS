# iceOS Setup Guide

## Prerequisites

- Python 3.10+
- Poetry (for dependency management)
- Docker (for Redis)
- API keys in `.env` file

## Quick Start

### 1. Install Dependencies

```bash
# Install all dependencies including LLM providers
poetry install --with dev --extras "llm_openai llm_anthropic"
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```env
# OpenAI (required for demos)
OPENAI_API_KEY=your-openai-api-key

# Optional: Other providers
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_API_KEY=your-google-api-key
```

### 3. Start the Development Server

```bash
# This will start Redis (if needed) and the API server
make dev
```

The server will be available at `http://localhost:8000`

### 4. MCP Server Setup (Optional)

iceOS can run as a **Model Context Protocol (MCP) server**, making it accessible to any MCP-compatible client (Claude Desktop, Continue, etc.).

#### HTTP MCP Server
```bash
# Start as HTTP MCP server
uvicorn ice_api.main:app --host 0.0.0.0 --port 8000

# MCP endpoint: http://localhost:8000/mcp/
# Health check: http://localhost:8000/health
```

#### Stdio MCP Server
```bash
# Start as stdio MCP server (for Claude Desktop integration)
python src/ice_api/mcp_stdio_server.py
```

#### Claude Desktop Integration
Add to your Claude Desktop `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "iceOS": {
      "command": "python",
      "args": ["/path/to/iceOS/src/ice_api/mcp_stdio_server.py"],
      "env": {
        "OPENAI_API_KEY": "your-api-key"
      }
    }
  }
}
```

👉 **[Complete MCP Documentation](MCP_IMPLEMENTATION.md)**

### 5. Run the Featured Demo

Experience the full power of iceOS with our production-ready Facebook Marketplace automation:

```bash
# Navigate to the enhanced demo
cd use-cases/RivaRidge/FB_Marketplace_Seller

# Run the complete demonstration
python enhanced_blueprint_demo.py

# Or explore specific features
python test_new_features.py        # Real HTTP APIs & activity simulation
python detailed_verification.py    # Comprehensive testing & validation
```

**What you'll see:**
- 🤖 Real GPT-4o API calls enhancing 20 inventory items
- 🌐 Actual HTTP requests to external APIs
- 🧠 Memory-enabled agents learning and adapting
- 🎭 Realistic marketplace ecosystem simulation
- ⚡ Both MCP Blueprint (enterprise) and SDK WorkflowBuilder (developer) patterns

**Results:** Complete end-to-end marketplace automation with ~$0.15-0.25 cost per run.

## Common Issues

### "No module named 'openai'"

Make sure you installed with the extras:
```bash
poetry install --extras "llm_openai"
```

### Redis not starting

Make sure Docker is running and port 6379 is free:
```bash
docker compose up -d redis
```

### Server not starting

Check that port 8000 is free:
```bash
lsof -i :8000
```

## Development Tips

1. Always use `poetry run` to ensure you're using the right environment
2. Run tests with: `make test`
3. Check code quality: `make doctor`
4. Format code: `make lint`

## Next Steps

- **[Explore the Complete Demo Documentation](../use-cases/RivaRidge/FB_Marketplace_Seller/README.md)** - Deep dive into the enhanced marketplace automation
- **[Architecture Notes](../use-cases/RivaRidge/FB_Marketplace_Seller/ARCHITECTURE_NOTES.md)** - Tools vs Agents decisions and memory architecture
- Check out the [Project Architecture Guide](ARCHITECTURE.md)
- Read about [Frosty and the Canvas](iceos-vision.md) 