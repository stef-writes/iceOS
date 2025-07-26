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

### 4. Run Demos

In a new terminal:

```bash
# Basic comprehensive demo
poetry run python examples/comprehensive_demo.py

# Advanced marketplace workflow demo
poetry run python examples/marketplace_workflow_demo.py
```

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

- Check out the [Architecture Guide](ARCHITECTURE.md)
- Browse example workflows in `examples/`
- Read about [Frosty and the Canvas](iceos-vision.md) 