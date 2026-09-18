#!/usr/bin/env python3
"""Query-drift detector for multi-hop research traces.

Takes a sequence of queries from a research session, embeds each with a
lightweight local TF-IDF embedder (numpy only, deterministic; clearly a
lexical baseline, not a neural model), and computes semantic drift of every
hop from the original intent:

    drift_i = 1 - cosine(query_i, query_0)

Hops with drift above --threshold are flagged. A trace whose drift keeps
climbing has wandered off the original question.

Usage:
  python3 drift.py [--trace trace.json] [--threshold 0.35]
"""
import argparse
import json
import os
import re

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

STOP = set("""a an the and or of to in on for with is are was were be as at by it
its this that these those from we you they he she his her their our your my
me him them us will would can could should shall may might do does did have
has had not no yes if then than so such into over under between each other
all any both few more most some only also very just about after before when
where which who whom whose what how why because while during per best buy to""".split())


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


class TfidfEmbedder:
    name = "count-vector baseline (lexical, no IDF: short queries)"

    def fit(self, docs):
        vocab = set()
        for toks in map(tokenize, docs):
            vocab.update(toks)
        self.vocab = {t: i for i, t in enumerate(sorted(vocab))}

    def encode(self, texts):
        mat = np.zeros((len(texts), len(self.vocab)))
        for i, text in enumerate(texts):
            toks = [t for t in tokenize(text) if t in self.vocab]
            if not toks:
                continue
            for t in set(toks):
                mat[i, self.vocab[t]] = toks.count(t) / len(toks)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return mat / norms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default=os.path.join(BASE, "trace.json"))
    ap.add_argument("--threshold", type=float, default=0.6)
    args = ap.parse_args()

    with open(args.trace) as f:
        data = json.load(f)

    print(f"embedder: {TfidfEmbedder.name}; drift threshold: {args.threshold}")
    for trace in data["traces"]:
        queries = trace["queries"]
        emb = TfidfEmbedder()
        emb.fit([trace["intent"]] + queries)
        vecs = emb.encode(queries)
        base = vecs[0]
        print(f"\ntrace: {trace['id']}")
        print(f"intent: {trace['intent']}")
        flagged = 0
        for i, q in enumerate(queries):
            drift = 1 - float(base @ vecs[i])
            flag = drift > args.threshold
            flagged += flag
            mark = "  <-- DRIFT" if flag else ""
            print(f"  hop {i}: drift={drift:.2f} {q}{mark}")
        print(f"  flagged hops: {flagged}/{len(queries)}")


if __name__ == "__main__":
    main()
