# Query-drift detector for multi-hop research traces

Flags when an agent's research queries wander off the original intent.

## How it works

`drift.py` reads a trace from `trace.json` (an ordered list of queries),
embeds each query with a lightweight local count-vector baseline (numpy only,
deterministic; lexical, not neural, and labeled as such), and computes per-hop
drift from the first query:

    drift_i = 1 - cosine(query_i, query_0)

Hops above `--threshold` (default 0.6) are flagged.

## Run

```bash
python3 drift.py
python3 drift.py --threshold 0.5 --trace my-trace.json
```

Needs numpy only.

## Measured result

Machine: Linux x86_64, AMD EPYC 9D25, Python 3.12.3.

| trace | hop drifts | flagged |
|---|---|---|
| trace-a (stays on batteries) | 0.00, 0.28, 0.54, 0.54, 0.23 | 0/5 |
| trace-b (drifts to stock picking) | 0.00, 0.28, 1.00, 1.00, 0.83 | 3/5 |

All three genuinely off-topic hops in trace B are flagged, none of the
on-topic hops in trace A are. Honest limitation: this is a lexical baseline,
so on-topic sub-questions that introduce new vocabulary (production
timeline, cycle life) still score 0.54. A neural embedder would separate
semantic drift from vocabulary shift better. The threshold is a tunable knob;
0.6 favors precision on this fixture.
