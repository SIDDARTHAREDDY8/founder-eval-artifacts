#!/usr/bin/env python3
"""Semantic vs fixed chunking benchmark.

Same corpus, same embedder, chunking strategy as the only variable.
Score: recall@k over a set of factoid queries whose answers sit in known
spans of the corpus.

Embedder: a lightweight local TF-IDF vectorizer (numpy only, deterministic).
It is clearly a lexical baseline, not a neural embedding model. Pass
--embedder st to use sentence-transformers instead, if installed.

Chunkers:
  fixed      word windows of --size with --overlap words of overlap
  semantic   sentence windows; a boundary is cut where cosine similarity
             between adjacent sentence windows drops below --threshold
  paragraph  split on blank lines (document structure baseline)

Usage:
  python3 bench.py [--chunkers fixed,semantic,paragraph] [--k 1 3]
"""
import argparse
import math
import os
import re

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

QUERIES = [
    ("Which Postgres version added row filtering on publications?",
     "Postgres 15 added row filtering on publications"),
    ("What LSN functions measure replication lag?",
     "pg_current_wal_lsn() on the primary with pg_last_wal_replay_lsn()",
     "on the standby"),
    ("What feeding ratio for a sourdough starter?",
     "1:2:2 ratio of starter to flour to water by weight"),
    ("Why avoid bleached flour for a starter?",
     "the bleaching process harms wild yeast"),
    ("How often bleed hydraulic bike brakes?",
     "Bleed hydraulic brakes once a year"),
    ("DOT vs mineral oil brake fluid?",
     "DOT and mineral oil are not interchangeable"),
]

STOP = set("""a an the and or of to in on for with is are was were be as at by it
its this that these those from we you they he she his her their our your my
me him them us will would can could should shall may might do does did have
has had not no yes if then than so such into over under between each other
all any both few more most some only also very just about after before when
where which who whom whose what how why because while during per""".split())


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


# ---------------- embedder (TF-IDF baseline, clearly labeled) ----------------

class TfidfEmbedder:
    name = "tfidf-baseline"

    def fit(self, docs):
        df = {}
        self.docs_tok = [tokenize(d) for d in docs]
        for toks in self.docs_tok:
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        self.vocab = {t: i for i, t in enumerate(sorted(df))}
        n = len(docs)
        self.idf = np.array(
            [math.log((1 + n) / (1 + df[t])) + 1.0 for t in sorted(df)])

    def encode(self, texts):
        mat = np.zeros((len(texts), len(self.vocab)))
        for i, text in enumerate(texts):
            toks = tokenize(text)
            if not toks:
                continue
            counts = {}
            for t in toks:
                if t in self.vocab:
                    counts[t] = counts.get(t, 0) + 1
            for t, c in counts.items():
                mat[i, self.vocab[t]] = (c / len(toks)) * self.idf[self.vocab[t]]
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return mat / norms


def get_embedder(kind):
    if kind == "tfidf":
        return TfidfEmbedder()
    if kind == "st":
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        class ST:  # noqa: D106
            name = "sentence-transformers/all-MiniLM-L6-v2"

            def fit(self, docs):
                pass

            def encode(self, texts):
                v = model.encode(texts, normalize_embeddings=True)
                return np.asarray(v)
        return ST()
    raise SystemExit(f"unknown embedder: {kind}")


# ---------------- chunkers ----------------

def chunk_fixed(text, size=60, overlap=10):
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + size]))
        i += size - overlap
    return chunks


def chunk_paragraph(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def chunk_semantic(text, embedder, threshold=0.15, min_words=30,
                   max_words=90):
    sents = sentences(text)
    if len(sents) < 2:
        return sents
    vecs = embedder.encode(sents)
    chunks, cur = [], [sents[0]]
    cur_words = len(sents[0].split())
    for i in range(1, len(sents)):
        sim = float(vecs[i - 1] @ vecs[i])
        w = len(sents[i].split())
        cut = ((sim < threshold and cur_words >= min_words)
               or cur_words + w > max_words)
        if cut and cur:
            chunks.append(" ".join(cur))
            cur, cur_words = [], 0
        cur.append(sents[i])
        cur_words += w
    if cur:
        chunks.append(" ".join(cur))
    return chunks


# ---------------- eval ----------------

def recall_at_k(chunks, vecs, qvec, gold, k):
    sims = vecs @ qvec
    top = np.argsort(sims)[::-1][:k]
    gold_n = re.sub(r"\s+", " ", gold.lower())
    for i in top:
        if gold_n in re.sub(r"\s+", " ", chunks[i].lower()):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunkers", default="fixed,semantic,paragraph")
    ap.add_argument("--k", type=int, nargs="+", default=[1, 3])
    ap.add_argument("--embedder", default="tfidf", choices=["tfidf", "st"])
    ap.add_argument("--size", type=int, default=60)
    ap.add_argument("--overlap", type=int, default=10)
    args = ap.parse_args()

    docs = []
    for fn in sorted(os.listdir(os.path.join(BASE, "corpus"))):
        if fn.endswith(".md"):
            with open(os.path.join(BASE, "corpus", fn)) as f:
                docs.append(f.read())
    full = "\n\n".join(docs)

    # fit the baseline embedder on sentence pieces (shared across chunkers)
    fit_docs = sentences(full)
    tmp = get_embedder(args.embedder)
    tmp.fit(fit_docs)

    chunkers = {
        "fixed": lambda: chunk_fixed(full, args.size, args.overlap),
        "semantic": lambda: chunk_semantic(full, tmp),
        "paragraph": lambda: chunk_paragraph(full),
    }

    print(f"embedder: {tmp.name} (same for all chunkers)")
    print(f"queries: {len(QUERIES)}, corpus docs: {len(docs)}")
    print()
    header = (f"{'chunker':<10}{'chunks':>7}{'avg_words':>10}" +
              "".join(f"{f'recall@{k}':>10}" for k in args.k))
    print(header)
    print("-" * len(header))
    for name in args.chunkers.split(","):
        chunks = chunkers[name]()
        vecs = tmp.encode(chunks)
        avg_w = sum(len(c.split()) for c in chunks) / max(len(chunks), 1)
        scores = []
        for q, *golds in QUERIES:
            gold = " ".join(golds)
            qvec = tmp.encode([q])[0]
            scores.append([recall_at_k(chunks, vecs, qvec, gold, k)
                           for k in args.k])
        rec = [sum(s[i] for s in scores) / len(scores) for i in range(len(args.k))]
        row = (f"{name:<10}{len(chunks):>7}{avg_w:>10.1f}" +
               "".join(f"{r:>10.2f}" for r in rec))
        print(row)


if __name__ == "__main__":
    main()
