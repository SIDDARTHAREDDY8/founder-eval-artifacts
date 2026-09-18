# Position-bias eval plugin (promptfoo-style)

Measures whether a RAG judge's score changes when the key chunk moves to
different positions in the context window.

## How it works

`positionBias.js` exports `measurePositionBias({ judge, chunks, keyId, question })`.
It builds the same context three ways (key chunk at start / middle / end),
calls the judge on each, and reports per-position scores, max spread, and a
verdict. `makePromptfooAssertion` wraps it as a promptfoo-compatible custom
assertion returning `{ pass, score, reason, namedScores }`.

## Run

```bash
node demo.mjs
```

No dependencies. The demo judge is SIMULATED (a deterministic function with
baked-in primacy bias), so the demo runs with no API cost. To use a real
judge, pass your own async `(context, question) => score` function.

## Measured result

With the simulated biased judge on the 3-case toy dataset:

| case | start | middle | end | max spread |
|---|---|---|---|---|
| Eiffel Tower | 1.00 | 0.88 | 0.76 | 0.24 |
| Calvin cycle | 1.00 | 0.88 | 0.76 | 0.24 |
| PostgreSQL MERGE | 1.00 | 0.88 | 0.76 | 0.24 |

Mean max spread: **0.24** -> verdict BIASED on all 3 cases. The plugin flags
it because 0.24 > 0.15 threshold. A position-fair judge would score ~0 spread.
