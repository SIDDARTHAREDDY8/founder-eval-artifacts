# Semantic vs fixed chunking benchmark

Same corpus, same embedder, chunking strategy as the only variable.
Score: recall@k over 6 factoid queries with known answer spans.

## How it works

`bench.py` chunks the 3-doc corpus (`corpus/`) three ways (fixed 60-word
windows with 10-word overlap, sentence-similarity semantic splits, paragraph
splits), embeds every chunk with one shared embedder, retrieves top-k per
query, and reports recall@k plus chunk counts and mean chunk size.

The default embedder is a lightweight local TF-IDF baseline (numpy only,
deterministic). It is a lexical baseline, not a neural embedding model, and
it is labeled as such in the output. Pass `--embedder st` to use
sentence-transformers (`all-MiniLM-L6-v2`) instead, if installed.

## Run

```bash
python3 bench.py
python3 bench.py --k 1 3 5 --embedder st
```

Needs numpy only for the default run.

## Measured result

Machine: Linux x86_64, AMD EPYC 9D25, Python 3.12.3, numpy 1.26.4.

| chunker | chunks | avg words | recall@1 | recall@3 | recall@5 |
|---|---|---|---|---|---|
| fixed | 11 | 54.0 | 0.83 | 0.83 | 0.83 |
| semantic | 14 | 35.9 | 0.83 | 0.83 | 0.83 |
| paragraph | 15 | 33.5 | 0.67 | 0.83 | 0.83 |

Honest read: on this small corpus with a lexical embedder, fixed windows and
semantic splits tie; paragraph splits trail at recall@1. One query ("What LSN
functions measure replication lag?") misses at every k under every chunker,
which is an embedder vocabulary gap, not a chunking difference. The harness
is the point: swap in your corpus, your embedder, and your chunkers, and the
table tells you what actually wins.
