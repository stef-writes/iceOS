# Benchmarks – ChatKit Bundle

This doc explains how to run a simple benchmark of the ChatKit RAG bundle and interpret the output.

## Prerequisites
- API running locally (e.g., `make demo-up` then `make demo-wait`)
- Example assets ingested (`make demo-ingest`) – optional but recommended

## Run
```bash
ICE_API_URL=http://localhost:8000 \
ICE_API_TOKEN=dev-token \
BENCH_QUERY="Summarize my resume" \
BENCH_WARMUPS=1 BENCH_RUNS=3 \
python scripts/ops/run_chatkit_bench.py
```

## Output
```json
{
  "runs": 3,
  "p50_latency_sec": 0.842,
  "avg_latency_sec": 0.901,
  "details": [
    {"status": "completed", "latency_sec": 0.92},
    {"status": "completed", "latency_sec": 0.84},
    {"status": "completed", "latency_sec": 0.94}
  ]
}
```

## Notes
- Set `ICEOS_EMBEDDINGS_PROVIDER=hash` for deterministic embeddings in CI.
- For consistent numbers, run on a warm API (after first request) and stable hardware.
- This measures end-to-end API execution, including orchestration and memory search.
