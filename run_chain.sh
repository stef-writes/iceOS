#!/bin/bash

API_URL="http://localhost:8000/api/v1/chains/execute"
JSON_PAYLOAD='{
  "context": {
    "text": "The quick brown fox jumps over the lazy dog. This is a test of our new word-counting tool and multi-model chain execution."
  },
  "nodes": [
    {
      "id": "word-counter",
      "type": "tool",
      "tool_name": "word_count",
      "output_schema": {
        "word_count": "int",
        "text": "str"
      }
    },
    {
      "id": "summarizer",
      "type": "ai",
      "model": "gpt-4",
      "provider": "openai",
      "llm_config": {
        "model": "gpt-4",
        "provider": "openai",
        "temperature": 0.3,
        "max_tokens": 64
      },
      "output_schema": {
        "text": "str"
      },
      "dependencies": ["word-counter"],
      "input_mappings": {
        "source_text": {
          "source_node_id": "word-counter",
          "source_output_key": "text"
        }
      },
      "prompt": "Summarize this text in one sentence: {source_text}"
    },
    {
      "id": "translator",
      "type": "ai",
      "model": "gemini-1.0-pro-latest",
      "provider": "google",
      "llm_config": {
        "model": "gemini-1.0-pro-latest",
        "provider": "google",
        "temperature": 0.3,
        "max_tokens": 64
      },
      "output_schema": {
        "text": "str"
      },
      "dependencies": ["summarizer"],
      "input_mappings": {
        "summary": {
          "source_node_id": "summarizer",
          "source_output_key": "text"
        }
      },
      "prompt": "Translate the following text into Spanish: {summary}"
    },
    {
      "id": "tweet-writer",
      "type": "ai",
      "model": "claude-3-opus-20240229",
      "provider": "anthropic",
      "llm_config": {
        "model": "claude-3-opus-20240229",
        "provider": "anthropic",
        "temperature": 0.7,
        "max_tokens": 80
      },
      "dependencies": ["translator"],
      "input_mappings": {
        "translated_summary": {
          "source_node_id": "translator",
          "source_output_key": "text"
        }
      },
      "prompt": "Create an engaging tweet about this Spanish summary: {translated_summary}"
    },
    {
      "id": "translation-wordcount",
      "type": "tool",
      "tool_name": "word_count",
      "dependencies": ["translator"],
      "input_mappings": {
        "text": {
          "source_node_id": "translator",
          "source_output_key": "text"
        }
      }
    }
  ],
  "persist_intermediate_outputs": true
}'

curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD"