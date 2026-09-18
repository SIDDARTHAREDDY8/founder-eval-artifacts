# Completion-pipeline latency profiler

Profiles a model-serving completion pipeline stage by stage and names the
bottleneck with real measured numbers.

## How it works

`mock_server.py` is a minimal HTTP completion server (stdlib only) with a
timed pipeline: parse, tokenize, queue, generate (streamed SSE tokens), each
timed with `perf_counter` and exposed via `GET /metrics`. It is a MOCK: no
real model sits behind it. The generate stage does a calibrated CPU busy-loop
per token, standing in for autoregressive decode.

`profile.py` starts the server, fires N requests, and measures on the client:
time to first token (TTFT) and per-token inter-arrival times from the SSE
stream. It then pulls the server stage timings and reports p50/p95 plus the
bottleneck stage.

## Run

```bash
python3 profile.py
python3 profile.py --requests 20 --max-tokens 32 --concurrency 4
```

Stdlib only. No dependencies.

## Measured result

Machine: Linux x86_64, AMD EPYC 9D25, Python 3.12.3. 20 requests, 32
tokens each, sequential.

| metric | p50 | p95 |
|---|---|---|
| client time to first token | 15.6 ms | 18.8 ms |
| client per-token latency (n=620) | 9.3 ms | 11.2 ms |

Server stage means: parse 0.0 ms, tokenize 0.0 ms, queue 4.7 ms,
generate 309.8 ms. Server decode per token: 9.6 ms mean, agreeing with the
client-side 9.3 ms. Bottleneck: **generate**, 98% of server time. That is the
honest finding of this mock: decode dominates, so batching or a faster
decode loop is where the wins are.
