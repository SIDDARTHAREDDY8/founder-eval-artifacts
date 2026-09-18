# founder-eval-artifacts

Seven small, runnable eval and profiling demos. Each one runs end to end,
prints real measured numbers, and ships with its own README.

Built by Siddartha Reddy Chinthala (M.S. Computer Science, University of
Cincinnati, Apr 2026). Every number below was measured by the code on the
machine noted with it: Linux x86_64 (AMD EPYC 9D25), Python 3.12.3, Node
v24.20.0. Simulated stand-ins are labeled SIMULATED wherever they appear.

## The artifacts

| # | Path | What it does | Run | Measured result |
|---|---|---|---|---|
| 1 | `01-sycophancy-drift/` | Multi-turn probe measuring how a model's stated stance drifts toward the user's suggested position | `python3 probe.py --backend stub-agreeable` | mean signed drift 36.0/100 (agreeable stub), 0.0 (firm stub); real models via `SYCOPHANCY_API_URL` |
| 2 | `02-position-bias-plugin/` | promptfoo-style plugin: moves the key RAG chunk to start/middle/end and checks judge score stability | `node demo.mjs` | mean max spread 0.24 across 3 cases, verdict BIASED (simulated judge) |
| 3 | `03-wait-for-content/` | Detects JS-heavy pages where naive extraction returns a partial page: raw-HTML snapshot vs headless-Chromium render | `python3 bench.py` | growth 6.95 on the JS fixture (PARTIAL), 1.0 on the static fixture; partial-page rate 1/2 |
| 4 | `04-chunking-bench/` | Fixed vs semantic vs paragraph chunking on one corpus, one embedder, recall@k | `python3 bench.py` | recall@1: fixed 0.83, semantic 0.83, paragraph 0.67 (TF-IDF baseline) |
| 5 | `05-query-drift/` | Flags multi-hop research queries that drift from the original intent (1 - cosine to query 0) | `python3 drift.py` | 3/3 off-topic hops flagged, 0/5 on-topic hops flagged |
| 6 | `06-completion-latency-profile/` | Profiles a mock completion pipeline per stage; reports p50/p95 token latency and the bottleneck | `python3 profile.py` | per-token p50 9.3 ms / p95 11.2 ms; bottleneck: generate (98% of server time) |
| 7 | `07-notebook-to-app-eval/` | Marimo notebook vs Streamlit app on the same data-app task: LOC, conversion checks, time to interactive | `python3 eval.py` | marimo 44 LOC vs streamlit 19 LOC; 7/7 conversion checks on both; 1.1 s vs 1.2 s to first HTTP 200 |

## Notes

- Where a real model or API would be needed, the demo uses a clearly
  labeled simulated stand-in and documents how to point it at a real one.
- Nothing here claims production experience. These are small harnesses that
  run, measure, and report.
